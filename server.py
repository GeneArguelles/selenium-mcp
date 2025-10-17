#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server (Render + Local Compatible)
# ==========================================================
# Provides headless browser automation for MCP-compatible
# agentic systems such as OpenAI Agent Builder.
# ----------------------------------------------------------
# Features:
#   • Dynamic LOCAL_MODE switch (macOS vs Render)
#   • Environment-driven Chrome & Driver paths
#   • Robust logging and health phases
#   • MCP-compliant schema for tool discovery
# ==========================================================

import os
import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
from pathlib import Path

# ----------------------------------------------------------
# Load environment variables
# ----------------------------------------------------------
load_dotenv()

app = FastAPI(title="Selenium MCP Server", version="1.0.0")

# ==========================================================
#  Environment & Path Configuration
# ==========================================================
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"
CHROME_VERSION = os.getenv("CHROME_VERSION", "120.0.6099.18")

if LOCAL_MODE:
    print("[INFO] 🧩 LOCAL_MODE enabled — using macOS Chrome paths")
    CHROME_BINARY = os.getenv("LOCAL_CHROME_BINARY", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    CHROMEDRIVER_PATH = os.getenv("LOCAL_CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
else:
    print("[INFO] 🧩 Render Mode — using sandbox Chrome paths")
    CHROME_BINARY = os.getenv("CHROME_BINARY", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "./chromedriver/chromedriver")

# ----------------------------------------------------------
# Server info metadata
# ----------------------------------------------------------
SERVER_NAME = os.getenv("SERVER_NAME", "Selenium")
SERVER_DESC = os.getenv("SERVER_DESC", "MCP server providing headless browser automation via Selenium.")
SERVER_VERSION = os.getenv("SERVER_VERSION", "1.0.0")
PYTHON_RUNTIME = f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"

# ----------------------------------------------------------
# Health check tracking
# ----------------------------------------------------------
PHASE = "starting"
START_TIME = time.time()


@app.on_event("startup")
async def startup_event():
    global PHASE
    PHASE = "starting"
    print("==========================================================")
    print(f"[INFO] Starting {SERVER_NAME} MCP Server...")
    print(f"[INFO] Description: {SERVER_DESC}")
    print(f"[INFO] Version: {SERVER_VERSION}")
    print(f"[INFO] Python Runtime: {PYTHON_RUNTIME}")
    print(f"[INFO] Chrome Binary: {CHROME_BINARY}")
    print(f"[INFO] Chrome Version (env): {CHROME_VERSION}")
    print("==========================================================")

    # Simulate warmup period
    time.sleep(2)
    PHASE = "ready"
    print("[INFO] Selenium MCP startup complete.")


# ==========================================================
# Routes
# ==========================================================

@app.get("/")
async def root():
    """Simple root endpoint for Render uptime pings."""
    return {
        "status": "running",
        "message": f"{SERVER_NAME} MCP Server is live.",
        "runtime": PYTHON_RUNTIME,
        "chrome_path": CHROME_BINARY,
        "phase": PHASE
    }


@app.post("/")
async def root_post():
    """Handle POST root discovery requests from OpenAI Agent Builder."""
    print("[INFO] POST / root discovery requested")
    return {
        "status": "ok",
        "message": f"{SERVER_NAME} MCP discovery acknowledged.",
        "phase": PHASE
    }


@app.get("/health")
async def health_check():
    """Render & local health endpoint."""
    uptime = time.time() - START_TIME
    return {
        "status": "healthy" if PHASE == "ready" else "starting",
        "phase": PHASE,
        "uptime_seconds": round(uptime, 2),
        "chrome_path": CHROME_BINARY
    }


@app.get("/mcp/schema")
@app.post("/mcp/schema")
async def mcp_schema():
    """Schema discovery endpoint (dual GET/POST for Agent Builder compatibility)."""
    print(f"[INFO] Served /mcp/schema for {SERVER_NAME} (Agent Builder spec compliant)")
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "type": "mcp_server",
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": SERVER_VERSION,
            "runtime": PYTHON_RUNTIME,
            "capabilities": {
                "invocation": True,
                "streaming": False,
                "multi_tool": False
            }
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        ]
    }
    return JSONResponse(content=schema)


@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """Tool invocation endpoint for headless Chrome operations."""
    try:
        payload = await request.json()
        tool = payload.get("tool")
        args = payload.get("arguments", {})

        if tool != "selenium_open_page":
            return JSONResponse(
                status_code=400,
                content={"detail": f"Unsupported tool: {tool}"}
            )

        url = args.get("url")
        if not url:
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing required 'url' argument."}
            )

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--remote-debugging-port=9222")

        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        title = driver.title
        driver.quit()

        return {"result": {"url": url, "title": title}}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Chrome could not start: {str(e)}"}
        )


# ==========================================================
# Entrypoint
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"[INFO] Starting Uvicorn on port {port} ...")
    uvicorn.run(app, host="0.0.0.0", port=port)

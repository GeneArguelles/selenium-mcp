#!/usr/bin/env python3
# ==============================================================
# Selenium MCP Server (Render-Safe Version)
# --------------------------------------------------------------
# - Runs FastAPI server compatible with Model Context Protocol
# - Uses a user-space Chromium binary (no apt-get required)
# - Provides full logging, health/status endpoints, and schema
# ==============================================================

import os
import time
import traceback
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import uvicorn

# ==============================================================
# GLOBALS
# ==============================================================

START_TIME = time.time()
LAST_INVOCATION = "No tool executed yet."

app = FastAPI(title="Selenium MCP Server", version="1.0.0")

# ==============================================================
# LOGGING UTILS
# ==============================================================

def log(msg: str):
    print(f"[INFO] {datetime.utcnow().isoformat()} | {msg}", flush=True)

# ==============================================================
# MCP ROOT ENDPOINT (for discovery)
# ==============================================================

@app.get("/")
async def root():
    """Root endpoint for Render health check."""
    uptime = round(time.time() - START_TIME, 2)
    return {
        "message": "🧩 Selenium MCP Server is alive.",
        "uptime_seconds": uptime,
        "docs": "/mcp/schema",
        "status": "/mcp/status",
    }

@app.post("/")
async def root_post():
    """POST root for MCP auto-discovery compatibility."""
    return await root()

# ==============================================================
# MCP SCHEMA ENDPOINT
# ==============================================================

@app.get("/mcp/schema")
@app.post("/mcp/schema")
async def mcp_schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": f"{os.getenv('PYTHON_VERSION', 'unknown')}"
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

# ==============================================================
# MCP STATUS ENDPOINT
# ==============================================================

@app.get("/mcp/status")
async def mcp_status():
    uptime = round(time.time() - START_TIME, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": LAST_INVOCATION,
        "server_time": datetime.utcnow().isoformat()
    }

# ==============================================================
# SELENIUM TOOL: OPEN PAGE
# ==============================================================

@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """
    Example MCP tool: opens a page in headless Chrome and returns the title.
    """
    global LAST_INVOCATION
    body = await request.json()
    tool = body.get("tool")
    args = body.get("arguments", {})

    if tool != "selenium_open_page":
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool}'")

    url = args.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing required argument: url")

    try:
        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")

        # Use the Render-safe, user-space Chrome binary
        chrome_binary = os.getenv(
            "CHROME_BINARY",
            "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
        )
        chrome_options.binary_location = chrome_binary

        log(f"Using Chrome binary: {chrome_binary}")

        # Initialize ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        title = driver.title
        driver.quit()

        LAST_INVOCATION = f"selenium_open_page({url}) at {datetime.utcnow().isoformat()}"
        return {"url": url, "title": title}

    except Exception as e:
        error_msg = f"500: Chrome could not start in current environment: {e}\n{traceback.format_exc()}"
        log(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# ==============================================================
# STARTUP HOOK
# ==============================================================

@app.on_event("startup")
async def startup_event():
    log("Launching Selenium MCP Server...")
    log(f"Python runtime: {os.getenv('PYTHON_VERSION', 'unknown')}")
    chrome_path = os.getenv("CHROME_BINARY", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
    log(f"Expecting Chrome binary at: {chrome_path}")
    log("Startup complete — awaiting requests.")

# ==============================================================
# ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    log(f"Starting MCP server on port {port} ...")
    time.sleep(1.5)  # small delay to let Render bind $PORT
    uvicorn.run(app, host="0.0.0.0", port=port)

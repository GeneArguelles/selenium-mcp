import os
import platform
import time
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# ==========================================================
# Load environment
# ==========================================================
load_dotenv()

# Runtime flags
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"
CHROME_VERSION = os.getenv("CHROME_VERSION", "120.0.6099.18")

# Paths
if LOCAL_MODE:
    CHROME_PATH = os.getenv(
        "LOCAL_CHROME_PATH",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    CHROMEDRIVER_PATH = os.getenv(
        "LOCAL_CHROMEDRIVER_PATH",
        "/usr/local/bin/chromedriver"
    )
else:
    CHROME_PATH = os.getenv(
        "CHROME_PATH",
        "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
    )
    CHROMEDRIVER_PATH = os.getenv(
        "CHROMEDRIVER_PATH",
        "/opt/render/project/src/chromedriver/chromedriver"
    )

# ==========================================================
# FastAPI initialization
# ==========================================================
app = FastAPI(title="Selenium MCP Server", version="1.0.0")
start_time = time.time()

# ==========================================================
# MCP Schema Endpoint (STRICT COMPLIANCE)
# ==========================================================
@app.post("/mcp/schema")
@app.get("/mcp/schema")
async def mcp_schema():
    """Serve the MCP schema (GET/POST) per Agent Builder spec"""
    schema = {
        "version": "2025-10-01",
        "type": "mcp",
        "server_info": {
            "name": "Selenium",
            "description": "MCP server providing headless browser automation via Selenium.",
            "version": "1.0.0",
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False
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
    print("[INFO] Served /mcp/schema for Selenium (Agent Builder compliant)")
    return JSONResponse(schema)

# ==========================================================
# MCP Invoke Endpoint
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    try:
        payload = await request.json()
        tool = payload.get("tool")
        args = payload.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse({"detail": "Missing URL parameter"}, status_code=400)
            title = await open_page_and_get_title(url)
            return JSONResponse({"result": {"url": url, "title": title}})

        return JSONResponse({"detail": f"Unknown tool: {tool}"}, status_code=400)

    except Exception as e:
        return JSONResponse({"detail": f"500: Chrome could not start: {e}"}, status_code=500)

# ==========================================================
# Helper Function: Launch Headless Chrome and Retrieve Title
# ==========================================================
async def open_page_and_get_title(url: str):
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        options.binary_location = CHROME_PATH

        driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=options)
        driver.get(url)
        title = driver.title
        driver.quit()
        return title

    except Exception as e:
        raise Exception(str(e))

# ==========================================================
# Health Endpoint (Render heartbeat)
# ==========================================================
@app.get("/health")
async def health():
    uptime = round(time.time() - start_time, 2)
    phase = "ready"
    return {
        "status": "healthy",
        "phase": phase,
        "uptime_seconds": uptime,
        "chrome_path": CHROME_PATH,
    }

# ==========================================================
# Root Endpoint (for Render root discovery)
# ==========================================================
@app.get("/")
@app.post("/")
async def root():
    print("[INFO] POST / root discovery requested")
    return {
        "status": "running",
        "message": "Selenium MCP Server is live.",
        "runtime": platform.python_version(),
        "chrome_path": CHROME_PATH,
    }

# ==========================================================
# Startup Logging
# ==========================================================
@app.on_event("startup")
async def startup_event():
    print("==========================================================")
    print("[INFO] Starting Selenium MCP Server...")
    print("[INFO] Description: MCP server providing headless browser automation via Selenium.")
    print("[INFO] Version: 1.0.0")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_PATH}")
    print(f"[INFO] Chrome Version (env): {CHROME_VERSION}")
    print("==========================================================")
    await asyncio.sleep(1)
    print("[INFO] Selenium MCP startup complete.")

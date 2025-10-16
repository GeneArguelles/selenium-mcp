#!/usr/bin/env python3
"""
Selenium MCP Server — Render-Ready
────────────────────────────────────────────
Features:
• ✅ /mcp/schema  — supports GET + POST (with server_info metadata)
• ✅ /mcp/ping    — quick health probe
• ✅ /mcp/status  — uptime + last invocation
• ✅ /mcp/debug   — environment sanity report
• ✅ /mcp/invoke  — runs selenium_open_page
────────────────────────────────────────────
"""

import os
import sys
import json
import time
import shutil
import platform
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from pyppeteer import chromium_downloader

# ---------------------------------------------------------------------
#  App & Global State
# ---------------------------------------------------------------------
app = FastAPI(title="Selenium MCP Server")
start_time = time.time()
last_invocation = "No tool executed yet."

# Enable CORS so Agent Builder can call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
#  Safe Chrome / Driver Initialization
# ---------------------------------------------------------------------
def init_chrome_driver():
    """Initialize a headless Chromium driver, even in restricted environments."""
    try:
        chromium_exec = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_exec):
            print("[INFO] Chromium not found — downloading...")
            chromium_downloader.download_chromium()

        # Relocate binary into /tmp (writable on Render)
        relocated_path = Path("/tmp/chromium/chrome")
        relocated_path.parent.mkdir(parents=True, exist_ok=True)
        if not relocated_path.exists():
            shutil.copy2(chromium_exec, relocated_path)
            os.chmod(relocated_path, 0o755)

        print(f"[INFO] Using Chromium binary: {relocated_path}")

        chrome_opts = Options()
        chrome_opts.binary_location = str(relocated_path)
        chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=chrome_opts)
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")

# ---------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Selenium MCP Server is alive. Use /mcp/schema to discover tools."}

@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema(request: Request):
    """Return MCP schema for OpenAI Agent Builder discovery."""
    schema = {
        "version": "2025-10-01",
        "server_info": {
            "name": "selenium_mcp_server",
            "description": "Render-hosted Selenium MCP exposing a browser automation tool.",
            "version": "1.0.0"
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            }
        ]
    }
    return JSONResponse(content=schema)

@app.get("/mcp/ping")
async def mcp_ping():
    """Simple heartbeat endpoint."""
    return {"status": "ok"}

@app.get("/mcp/status")
async def mcp_status():
    """Return uptime and last invocation."""
    uptime = round(time.time() - start_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": datetime.utcnow().isoformat()
    }

@app.get("/mcp/debug")
async def mcp_debug():
    """Environment diagnostics for Render sandbox sanity check."""
    chromium_exec = chromium_downloader.chromium_executable()
    relocated_path = "/tmp/chromium/chrome"
    result = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "home": os.getenv("HOME"),
        "path_env": os.getenv("PATH"),
        "chromium_exec": chromium_exec,
        "chrome_exists": os.path.exists(chromium_exec),
        "relocated_path": relocated_path,
        "relocated_exists": os.path.exists(relocated_path),
        "which_chromedriver": shutil.which("chromedriver"),
        "which_chrome": shutil.which("chrome"),
        "which_chromium": shutil.which("chromium"),
    }
    return JSONResponse(content=result)

@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """Execute an MCP tool invocation."""
    global last_invocation
    try:
        payload = await request.json()
        tool = payload.get("tool")
        args = payload.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"error": "Missing URL argument"})

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            last_invocation = f"selenium_open_page({url}) @ {datetime.utcnow().isoformat()}"
            return {"ok": True, "url": url, "title": title}

        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown tool '{tool}'"})

    except Exception as e:
        last_invocation = f"Failed: {e}"
        print(f"[ERROR] Exception during tool invocation: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

# ---------------------------------------------------------------------
#  Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting Selenium MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

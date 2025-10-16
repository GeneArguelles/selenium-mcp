#!/usr/bin/env python3
"""
Selenium MCP Server — Render-ready + Agent Builder compatible
• GET+POST /mcp/schema  → Tool discovery handshake
• /mcp/ping             → Health check
• /mcp/debug            → Environment inspection
• /mcp/invoke           → Execute Selenium tool
• /mcp/status           → Uptime & last-invocation monitor
"""

import os
import sys
import json
import shutil
import time
import platform
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pyppeteer import chromium_downloader

# ---------------------------------------------------------------------
#  App initialization
# ---------------------------------------------------------------------
app = FastAPI(title="Selenium MCP Server")

# Enable CORS (Agent Builder requires cross-origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
#  Global state
# ---------------------------------------------------------------------
SERVER_START_TIME = time.time()
LAST_INVOCATION = None


# ---------------------------------------------------------------------
#  Safe Chrome / Driver Initialization
# ---------------------------------------------------------------------
def init_chrome_driver():
    """Initialize a headless Chromium driver in Render’s sandbox."""
    try:
        chromium_exec = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_exec):
            print("[INFO] Chromium not found — downloading...")
            chromium_downloader.download_chromium()

        # Relocate binary into /tmp (Render writable path)
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

@app.get("/mcp/ping")
async def ping():
    """Simple health check for uptime monitoring."""
    return {"status": "ok"}


@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema(request: Request):
    """
    Return MCP schema for OpenAI Agent Builder discovery.
    Supports both GET and POST for handshake compatibility.
    """
    schema = {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }
    return JSONResponse(content=schema)


@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """Handle invocation of a registered MCP tool."""
    global LAST_INVOCATION
    try:
        data = await request.json()
        tool = data.get("tool")
        args = data.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"detail": "Missing 'url' argument."})

            print(f"[INFO] Opening page: {url}")
            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            LAST_INVOCATION = {
                "tool": tool,
                "url": url,
                "title": title,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return {"ok": True, "url": url, "title": title}

        else:
            return JSONResponse(status_code=404, content={"detail": f"Unknown tool: {tool}"})

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Recovered from Chrome failure: {e}"})


@app.get("/mcp/debug")
async def debug():
    """Expose environment paths and Chrome availability for Render sandbox sanity checks."""
    try:
        chromium_exec = chromium_downloader.chromium_executable()
        exists = os.path.exists(chromium_exec)
        relocated_path = "/tmp/chromium/chrome"
        relocated_exists = os.path.exists(relocated_path)
        which_driver = shutil.which("chromedriver")

        result = {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cwd": os.getcwd(),
            "home": str(Path.home()),
            "path_env": os.environ.get("PATH"),
            "chromium_exec": chromium_exec,
            "chrome_exists": exists,
            "relocated_path": relocated_path,
            "relocated_exists": relocated_exists,
            "which_chromedriver": which_driver,
        }
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/mcp/status")
async def status():
    """Return uptime and last invocation details."""
    uptime = round(time.time() - SERVER_START_TIME, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": LAST_INVOCATION or "No tool executed yet.",
        "server_time": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    return {"message": "Selenium MCP Server is live."}

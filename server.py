#!/usr/bin/env python3
"""
Selenium MCP Server — Render-Stable + Agent Builder Compliant Version
────────────────────────────────────────────────────────────────────────────
Features:
• POST /                 – MCP handshake ("type": "mcp_server")
• /mcp/schema (GET+POST) – Tool discovery
• /mcp/invoke            – Executes Selenium headless task
• /mcp/ping              – Health probe
• /mcp/status            – Uptime + last invocation
• /mcp/debug             – Environment diagnostics
────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import time
import json
import shutil
import platform
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pyppeteer import chromium_downloader


# ─────────────────────────────────────────────────────────────
#   App + Globals
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="Selenium MCP Server")
start_time = time.time()
last_invocation = "No tool executed yet."

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#   Safe Chrome / Driver Initialization
# ─────────────────────────────────────────────────────────────
def init_chrome_driver():
    """Initialize a headless Chromium driver (stable for Render sandbox)."""
    try:
        chromium_exec = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_exec):
            print("[INFO] Chromium not found — downloading...")
            chromium_downloader.download_chromium()

        # Copy to writable /tmp path (Render restriction workaround)
        relocated_path = Path("/tmp/chromium/chrome")
        relocated_path.parent.mkdir(parents=True, exist_ok=True)
        if not relocated_path.exists():
            shutil.copy2(chromium_exec, relocated_path)
            os.chmod(relocated_path, 0o755)

        print(f"[INFO] Using Chromium binary: {relocated_path}")

        # 🧩 Stable Headless Options for Render / Heroku / Docker
        chrome_opts = Options()
        chrome_opts.binary_location = str(relocated_path)
        chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--disable-gpu")
        chrome_opts.add_argument("--disable-software-rasterizer")
        chrome_opts.add_argument("--disable-features=VizDisplayCompositor")
        chrome_opts.add_argument("--remote-debugging-port=9222")
        chrome_opts.add_argument("--window-size=1280,720")
        chrome_opts.add_argument("--disable-extensions")
        chrome_opts.add_argument("--disable-translate")
        chrome_opts.add_argument("--disable-background-networking")
        chrome_opts.add_argument("--disable-sync")
        chrome_opts.add_argument("--disable-web-security")
        chrome_opts.add_argument("--disable-default-apps")
        chrome_opts.add_argument("--mute-audio")
        chrome_opts.add_argument("--user-data-dir=/tmp/chrome-user-data")  # ✅ Critical

        driver = webdriver.Chrome(options=chrome_opts)
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")


# ─────────────────────────────────────────────────────────────
#   Endpoints
# ─────────────────────────────────────────────────────────────
@app.get("/")
async def root_get():
    """Simple landing page."""
    return {
        "message": "Selenium MCP Server is alive.",
        "hint": "POST / for MCP handshake or visit /mcp/schema."
    }


@app.post("/")
async def root_post():
    """
    MCP root POST — required by OpenAI Agent Builder handshake.
    """
    return JSONResponse(
        content={
            "type": "mcp_server",   # ✅ required for Agent Builder discovery
            "version": "2025-10-01",
            "server_info": {
                "name": "selenium_mcp_server",
                "description": "Root MCP endpoint for OpenAI Agent Builder compatibility.",
                "version": "1.0.0"
            },
            "endpoints": [
                "/mcp/schema",
                "/mcp/invoke",
                "/mcp/ping",
                "/mcp/status",
                "/mcp/debug"
            ]
        }
    )


@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema(request: Request):
    """Return MCP schema for Agent Builder discovery."""
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "name": "selenium_mcp_server",
            "description": "Render-hosted Selenium MCP exposing a headless browser automation tool.",
            "version": "1.0.0"
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
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


@app.get("/mcp/ping")
async def mcp_ping():
    """Simple heartbeat."""
    return {"status": "ok"}


@app.get("/mcp/status")
async def mcp_status():
    """Report uptime and last tool invocation."""
    uptime = round(time.time() - start_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": datetime.utcnow().isoformat()
    }


@app.get("/mcp/debug")
async def mcp_debug():
    """System + environment diagnostics for Render sandbox."""
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


# ─────────────────────────────────────────────────────────────
#   Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting Selenium MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

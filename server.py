#!/usr/bin/env python3
"""
Selenium MCP Server — Render-ready version
• Supports GET + POST /mcp/schema   (Agent Builder discovery)
• Includes /mcp/ping                (health check)
• Includes /mcp/debug               (environment sanity check)
• Provides /mcp/invoke              (tool execution)
"""

import os
import sys
import json
import shutil
import platform
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from pyppeteer import chromium_downloader

app = FastAPI(title="Selenium MCP Server")

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

        # Relocate binary into /tmp (writable path)
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
#  MCP Schema (now supports both GET and POST)
# ---------------------------------------------------------------------
MCP_SCHEMA = {
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

@app.get("/mcp/schema")
@app.post("/mcp/schema")
async def get_schema(request: Request):
    """Return static MCP schema (supports GET + POST for Agent Builder)."""
    return MCP_SCHEMA

# ---------------------------------------------------------------------
#  MCP Invoke
# ---------------------------------------------------------------------
@app.post("/mcp/invoke")
async def invoke_tool(request: Request):
    """Invoke MCP tools by name."""
    try:
        body = await request.json()
        tool = body.get("tool")
        args = body.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse({"error": "Missing URL"}, status_code=400)

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"result": title}

        return JSONResponse({"error": f"Unknown tool: {tool}"}, status_code=404)

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        return JSONResponse({"detail": f"Recovered from Chrome failure: {e}"}, status_code=500)

# ---------------------------------------------------------------------
#  MCP Debug — Environment Sanity Check
# ---------------------------------------------------------------------
@app.get("/mcp/debug")
def debug_info():
    chromium_exec = chromium_downloader.chromium_executable()
    relocated = Path("/tmp/chromium/chrome")
    chrome_exists = Path(chromium_exec).exists()
    relocated_exists = relocated.exists()
    version_output = None
    status_code = None
    try:
        import subprocess
        version_output = subprocess.check_output(
            [str(relocated), "--version"], text=True
        ).strip()
        status_code = 0
    except Exception as e:
        version_output = str(e)
        status_code = 1

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
        "path_env": os.environ.get("PATH"),
        "chromium_exec": chromium_exec,
        "chrome_exists": chrome_exists,
        "relocated_path": str(relocated),
        "relocated_exists": relocated_exists,
        "chrome_version_output": version_output,
        "chrome_exec_status": status_code,
        "which_chromedriver": shutil.which("chromedriver"),
        "which_chrome": shutil.which("chrome"),
        "which_chromium": shutil.which("chromium"),
    }

# ---------------------------------------------------------------------
#  MCP Ping — Health Check
# ---------------------------------------------------------------------
@app.get("/mcp/ping")
def ping():
    """Lightweight health endpoint for uptime checks."""
    return {"status": "ok"}

# ---------------------------------------------------------------------
#  Root
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Selenium MCP Server active — see /mcp/schema, /mcp/debug, /mcp/ping"}

# ---------------------------------------------------------------------
#  Local Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

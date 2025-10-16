#!/usr/bin/env python3
"""
Render-Safe Selenium MCP Server
• Provides a root `/` endpoint for Render health checks
• Binds automatically to Render's $PORT environment variable
• Includes Chrome startup safety delay & detailed logging
• Exposes standard MCP endpoints: /mcp/ping, /mcp/schema, /mcp/invoke, /mcp/status
"""

import os
import sys
import time
import json
import platform
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------
#  FastAPI Application Setup
# ---------------------------------------------------------------------
app = FastAPI(title="Selenium MCP Server", version="1.0.0")

startup_time = time.time()
last_invocation = "No tool executed yet."


# ---------------------------------------------------------------------
#  Utility: Initialize Chrome WebDriver (Render Safe)
# ---------------------------------------------------------------------
def init_chrome_driver():
    """Initialize a headless Chrome WebDriver suitable for Render."""
    print("[INFO] Initializing Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1280,720")

    chrome_binary = "/usr/bin/google-chrome"
    if os.path.exists(chrome_binary):
        chrome_options.binary_location = chrome_binary
        print(f"[INFO] Found Chrome binary at: {chrome_binary}")
    else:
        print("[WARN] Chrome binary not found at /usr/bin/google-chrome.")
        print("[WARN] Attempting to continue using system default ChromeDriver.")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("[INFO] Chrome WebDriver successfully initialized.")
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")


# ---------------------------------------------------------------------
#  MCP Endpoints
# ---------------------------------------------------------------------
@app.get("/")
async def root():
    """Basic root route for Render health check."""
    return {"ok": True, "service": "Selenium MCP Server", "runtime": platform.python_version()}


@app.get("/mcp/ping")
async def ping():
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/mcp/schema")
@app.get("/mcp/schema")
async def schema():
    """Return MCP schema for discovery."""
    schema = {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": platform.python_version(),
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }
    return JSONResponse(schema)


@app.post("/mcp/invoke")
async def invoke(request: Request):
    """Invoke MCP tools."""
    global last_invocation
    data = await request.json()
    tool = data.get("tool")
    args = data.get("arguments", {})

    if tool == "selenium_open_page":
        url = args.get("url")
        if not url:
            return JSONResponse({"error": "Missing 'url' parameter."}, status_code=400)

        try:
            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()
            last_invocation = f"Opened {url}"
            return {"ok": True, "url": url, "title": title}
        except Exception as e:
            last_invocation = f"Failed: {e}"
            return JSONResponse({"detail": f"500: Chrome could not start in current environment: {e}"}, status_code=500)

    return JSONResponse({"error": f"Unknown tool: {tool}"}, status_code=400)


@app.get("/mcp/status")
async def status():
    """Report uptime, last invocation, and runtime details."""
    uptime = round(time.time() - startup_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python_version": platform.python_version(),
    }


# ---------------------------------------------------------------------
#  Entry Point for Render
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("[INFO] Starting Selenium MCP Server...")
    print("[INFO] Waiting briefly to allow system services to settle...")
    time.sleep(5)

    port = int(os.getenv("PORT", "10000"))
    print(f"[INFO] Binding server to 0.0.0.0:{port}")
    print("[INFO] Launching Uvicorn...")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

#!/usr/bin/env python3
"""
Render-safe Selenium MCP Server
Auto-detects and version-matches Chrome + ChromeDriver
"""

import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pydantic import BaseModel
import uvicorn

# ======================================================
# Configuration
# ======================================================

app = FastAPI(title="Selenium MCP Server", version="1.0.0")

CHROME_BINARY = os.getenv(
    "CHROME_BINARY", "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
)
PORT = int(os.getenv("PORT", "10000"))

# ======================================================
# Models
# ======================================================

class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ======================================================
# Logging Utilities
# ======================================================

def log(msg: str):
    print(f"[INFO] {msg}", flush=True)

# ======================================================
# Root Endpoint
# ======================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>✅ Selenium MCP Server is live on Render!</h2>"

# ======================================================
# MCP Ping
# ======================================================

@app.get("/mcp/ping")
async def mcp_ping():
    return {"status": "ok"}

# ======================================================
# MCP Schema
# ======================================================

@app.post("/mcp/schema")
async def mcp_schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": os.popen("python3 --version").read().strip(),
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

# ======================================================
# MCP Status
# ======================================================

START_TIME = time.time()
LAST_INVOCATION = "No tool executed yet."

@app.get("/mcp/status")
async def mcp_status():
    return {
        "status": "running",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "last_invocation": LAST_INVOCATION,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

# ======================================================
# MCP Invoke
# ======================================================

@app.post("/mcp/invoke")
async def mcp_invoke(request: InvokeRequest):
    global LAST_INVOCATION

    if request.tool != "selenium_open_page":
        return JSONResponse(status_code=400, content={"detail": f"Unknown tool: {request.tool}"})

    url = request.arguments.get("url")
    if not url:
        return JSONResponse(status_code=400, content={"detail": "Missing 'url' parameter"})

    try:
        # --------------------------------------------------
        # Chrome Options
        # --------------------------------------------------
        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")

        log(f"Launching Chrome via binary: {CHROME_BINARY}")

        # --------------------------------------------------
        # Match ChromeDriver version to installed Chrome
        # --------------------------------------------------
        log("Resolving ChromeDriver version automatically...")
        service = Service(ChromeDriverManager(driver_version="latest").install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        title = driver.title
        driver.quit()

        LAST_INVOCATION = f"Success: selenium_open_page → {url}"
        return {"result": {"url": url, "title": title}}

    except Exception as e:
        LAST_INVOCATION = f"Failed: {str(e)}"
        return JSONResponse(status_code=500, content={"detail": f"500: Chrome could not start in current environment: {str(e)}"})

# ======================================================
# Startup
# ======================================================

if __name__ == "__main__":
    log("Starting Render-safe Selenium MCP Server...")
    log(f"Using Chrome binary: {CHROME_BINARY}")
    log(f"Python runtime: {os.popen('python3 --version').read().strip()}")
    log(f"Binding to PORT={PORT} ...")
    time.sleep(1)
    uvicorn.run(app, host="0.0.0.0", port=PORT)

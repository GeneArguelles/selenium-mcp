#!/usr/bin/env python3
"""
Render-safe Selenium MCP Server
Auto-matches ChromeDriver version to installed Chromium binary (v120+ safe)
"""

import os
import time
import subprocess
import requests
import zipfile
from io import BytesIO
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Selenium MCP Server", version="1.0.0")

# ======================================================
# Configuration
# ======================================================

CHROME_BINARY = os.getenv(
    "CHROME_BINARY", "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
)
PORT = int(os.getenv("PORT", "10000"))
CHROMEDRIVER_PATH = "/opt/render/project/src/.local/chromedriver/chromedriver"

os.makedirs(os.path.dirname(CHROMEDRIVER_PATH), exist_ok=True)

# ======================================================
# Utility Logging
# ======================================================

def log(msg: str):
    print(f"[INFO] {msg}", flush=True)

def get_chrome_version():
    try:
        result = subprocess.run(
            [CHROME_BINARY, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        version_str = result.stdout.strip()
        log(f"Detected Chrome version: {version_str}")
        return version_str.split()[2]  # e.g. "120.0.6099.18"
    except Exception as e:
        log(f"[WARN] Unable to detect Chrome version: {e}")
        return None

def download_matching_chromedriver(version):
    major_version = version.split(".")[0]
    base_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip"
    fallback_url = f"https://storage.googleapis.com/chrome-for-testing-public/{major_version}.0.6099.18/linux64/chromedriver-linux64.zip"

    for url in [base_url, fallback_url]:
        log(f"Attempting to fetch ChromeDriver from: {url}")
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                with zipfile.ZipFile(BytesIO(resp.content)) as z:
                    z.extractall(os.path.dirname(CHROMEDRIVER_PATH))
                log("✅ ChromeDriver extracted successfully.")
                return True
        except Exception as e:
            log(f"[WARN] ChromeDriver fetch failed: {e}")
    return False

# ======================================================
# Models
# ======================================================

class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ======================================================
# Root
# ======================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>✅ Selenium MCP Server (auto-matching driver) is live!</h2>"

# ======================================================
# Ping
# ======================================================

@app.get("/mcp/ping")
async def ping():
    return {"status": "ok"}

# ======================================================
# Schema
# ======================================================

@app.post("/mcp/schema")
async def schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.1",
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
# Status
# ======================================================

START_TIME = time.time()
LAST_INVOCATION = "No tool executed yet."

@app.get("/mcp/status")
async def status():
    return {
        "status": "running",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "last_invocation": LAST_INVOCATION,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

# ======================================================
# Invoke
# ======================================================

@app.post("/mcp/invoke")
async def invoke(req: InvokeRequest):
    global LAST_INVOCATION

    if req.tool != "selenium_open_page":
        return JSONResponse(status_code=400, content={"detail": "Unknown tool"})

    url = req.arguments.get("url")
    if not url:
        return JSONResponse(status_code=400, content={"detail": "Missing 'url'"})

    try:
        # Ensure driver version match
        version = get_chrome_version()
        if not version or not os.path.exists(CHROMEDRIVER_PATH):
            if not download_matching_chromedriver(version):
                raise RuntimeError("Failed to download matching ChromeDriver")

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        title = driver.title
        driver.quit()

        LAST_INVOCATION = f"Success: selenium_open_page → {url}"
        return {"result": {"url": url, "title": title}}

    except Exception as e:
        LAST_INVOCATION = f"Failed: {str(e)}"
        return JSONResponse(
            status_code=500,
            content={"detail": f"500: Chrome could not start in current environment: {str(e)}"},
        )

# ======================================================
# Startup
# ======================================================

if __name__ == "__main__":
    log("Starting Render-safe Selenium MCP Server (auto-matching ChromeDriver)...")
    version = get_chrome_version()
    if version:
        download_matching_chromedriver(version)
    log(f"Using Chrome binary: {CHROME_BINARY}")
    log(f"Python runtime: {os.popen('python3 --version').read().strip()}")
    log(f"Binding to PORT={PORT} ...")
    time.sleep(1)
    uvicorn.run(app, host="0.0.0.0", port=PORT)

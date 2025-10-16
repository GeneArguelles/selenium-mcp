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

app = FastAPI(title="Selenium MCP Server", version="1.0.2")

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

# ======================================================
# Chrome Version + Driver Sync
# ======================================================

def get_chrome_version():
    """Return version string like '120.0.6099.18', or None if detection fails."""
    try:
        # Ensure binary exists and is executable
        if not os.path.exists(CHROME_BINARY):
            log(f"[WARN] Chrome binary not found at {CHROME_BINARY}")
            return None
        os.chmod(CHROME_BINARY, 0o755)

        result = subprocess.run(
            [CHROME_BINARY, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        version_str = result.stdout.strip()
        if not version_str:
            log(f"[WARN] Chrome version output empty. stderr: {result.stderr.strip()}")
            return None
        log(f"Detected Chrome version: {version_str}")
        # Typical output: 'Chromium 120.0.6099.18'
        version = version_str.split()[1]
        return version
    except Exception as e:
        log(f"[WARN] Unable to detect Chrome version: {e}")
        return None


def download_matching_chromedriver(version):
    """Download and extract the exact ChromeDriver matching the version."""
    if not version:
        log("[ERROR] No Chrome version detected. Skipping ChromeDriver download.")
        return False

    try:
        major_version = version.split(".")[0]
    except Exception:
        log(f"[WARN] Invalid version format: {version}")
        return False

    urls = [
        f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip",
        f"https://storage.googleapis.com/chrome-for-testing-public/{major_version}.0.6099.18/linux64/chromedriver-linux64.zip",
    ]

    for url in urls:
        log(f"Attempting ChromeDriver download from: {url}")
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                with zipfile.ZipFile(BytesIO(resp.content)) as z:
                    z.extractall(os.path.dirname(CHROMEDRIVER_PATH))
                log("✅ ChromeDriver extracted successfully.")
                return True
            else:
                log(f"[WARN] HTTP {resp.status_code} from {url}")
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
            "version": "1.0.2",
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
        version = get_chrome_version()
        if not version or not os.path.exists(CHROMEDRIVER_PATH):
            if not download_matching_chromedriver(version):
                raise RuntimeError("Failed to download or detect matching ChromeDriver")

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        log(f"Starting Chrome using driver: {CHROMEDRIVER_PATH}")
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
    log("Starting Render-safe Selenium MCP Server (resilient version detection)...")
    version = get_chrome_version()
    if version:
        download_matching_chromedriver(version)
    else:
        log("[WARN] Chrome version undetectable; driver download skipped.")
    log(f"Using Chrome binary: {CHROME_BINARY}")
    log(f"Python runtime: {os.popen('python3 --version').read().strip()}")
    log(f"Binding to PORT={PORT} ...")
    time.sleep(1)
    uvicorn.run(app, host="0.0.0.0", port=PORT)

#!/usr/bin/env python3
# ============================================================
# server.py — Selenium MCP Server with runtime Chrome fetch
# ============================================================

import os
import time
import subprocess
import tarfile
import tempfile
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI(title="Selenium MCP Server")
start_time = time.time()
last_invocation = "No tool executed yet."


# ============================================================
# Download and extract Chrome for Testing at runtime
# ============================================================

def download_chrome_runtime():
    """Download a portable Chrome build into /tmp/chrome if not present."""
    chrome_dir = "/tmp/chrome"
    chrome_bin = os.path.join(chrome_dir, "chrome")

    if os.path.exists(chrome_bin):
        print(f"[INFO] Reusing existing Chrome binary at {chrome_bin}")
        return chrome_bin

    print("[INFO] Downloading Chrome for Testing runtime...")
    url = (
        "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/"
        "linux64/chrome-linux64.zip"
    )
    zip_path = os.path.join(tempfile.gettempdir(), "chrome.zip")

    # download zip
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    # extract zip
    os.makedirs(chrome_dir, exist_ok=True)
    subprocess.run(["unzip", "-o", zip_path, "-d", chrome_dir], check=True)

    chrome_path = os.path.join(chrome_dir, "chrome-linux64", "chrome")
    if not os.path.exists(chrome_path):
        raise RuntimeError("Failed to extract Chrome binary.")

    # symlink to /tmp/chrome/chrome for consistent path
    os.symlink(chrome_path, chrome_bin)
    print(f"[INFO] Chrome downloaded to {chrome_bin}")
    return chrome_bin


# ============================================================
# Initialize Chrome driver
# ============================================================

def init_chrome_driver():
    """
    Initialize headless Chrome safely on Render.
    Uses Chrome-for-Testing runtime if system Chrome missing.
    """
    chrome_opts = Options()
    chrome_path = None

    # Try common system paths first
    for path in [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]:
        if os.path.exists(path):
            chrome_path = path
            break

    # Otherwise fetch runtime build
    if not chrome_path:
        chrome_path = download_chrome_runtime()

    chrome_opts.binary_location = chrome_path
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-software-rasterizer")
    chrome_opts.add_argument("--window-size=1920,1080")

    print(f"[INFO] Launching Chrome from {chrome_path}")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_opts)
        print("[INFO] Chrome successfully started.")
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")


# ============================================================
# MCP Routes
# ============================================================

@app.get("/")
async def root():
    return {"message": "Selenium MCP Server (runtime Chrome) is live."}


@app.get("/mcp/ping")
async def ping():
    return {"status": "ok"}


@app.post("/mcp/schema")
async def schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP with runtime Chrome download.",
            "version": "1.1.0",
            "runtime": "3.11.9",
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in headless Chrome and return the title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }


@app.post("/mcp/invoke")
async def invoke(request: Request):
    global last_invocation
    try:
        body = await request.json()
        tool = body.get("tool")
        args = body.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse({"detail": "Missing 'url'."}, 400)

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            last_invocation = f"selenium_open_page → {url}"
            return {"ok": True, "url": url, "title": title}

        return JSONResponse({"detail": f"Unknown tool {tool}"}, 400)
    except Exception as e:
        last_invocation = f"Failed: {e}"
        return JSONResponse({"detail": f"500: Chrome could not start in current environment: {e}"}, 500)


@app.get("/mcp/status")
async def status():
    uptime = round(time.time() - start_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ============================================================
# Launch
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Launching Selenium MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=10000)

#!/usr/bin/env python3
"""
Render-safe Selenium MCP Server
Bypasses driver auto-detection, explicitly defines Chrome + ChromeDriver paths.
Includes /mcp/debug endpoint for runtime diagnostics.
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

app = FastAPI(title="Selenium MCP Server", version="1.0.5")

# ======================================================
# CONFIGURATION
# ======================================================

CHROME_BINARY = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
CHROMEDRIVER_DIR = "/tmp/chromedriver"
CHROMEDRIVER_PATH = os.path.join(CHROMEDRIVER_DIR, "chromedriver")
PORT = int(os.getenv("PORT", "10000"))

os.makedirs(CHROMEDRIVER_DIR, exist_ok=True)

# Disable all Selenium auto-driver lookups
os.environ["WDM_LOG_LEVEL"] = "0"
os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_DRIVER"] = CHROMEDRIVER_PATH
os.environ["PATH"] = f"{CHROMEDRIVER_DIR}:{os.environ.get('PATH', '')}"

# ======================================================
# HELPERS
# ======================================================

def log(msg: str):
    print(f"[INFO] {msg}", flush=True)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)

def get_chrome_version():
    if not os.path.exists(CHROME_BINARY):
        log(f"[WARN] Chrome binary not found at {CHROME_BINARY}")
        return None
    os.chmod(CHROME_BINARY, 0o755)
    out, err = run_cmd([CHROME_BINARY, "--version"])
    if not out:
        log(f"[WARN] Chrome version output empty: {err}")
        return None
    log(f"Detected Chrome version string: {out}")
    try:
        return out.split()[1]
    except Exception:
        return None

def download_driver(version):
    if not version:
        log("[ERROR] No Chrome version detected.")
        return False
    major = version.split(".")[0]
    urls = [
        f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip",
        f"https://storage.googleapis.com/chrome-for-testing-public/{major}.0.6099.18/linux64/chromedriver-linux64.zip",
    ]
    for url in urls:
        try:
            log(f"Downloading ChromeDriver from {url}")
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                with zipfile.ZipFile(BytesIO(r.content)) as z:
                    z.extractall(CHROMEDRIVER_DIR)
                for root, _, files in os.walk(CHROMEDRIVER_DIR):
                    if "chromedriver" in files:
                        path = os.path.join(root, "chromedriver")
                        os.chmod(path, 0o755)
                        log(f"✅ ChromeDriver ready at {path}")
                        return True
            else:
                log(f"[WARN] HTTP {r.status_code} when fetching {url}")
        except Exception as e:
            log(f"[WARN] Driver fetch failed: {e}")
    return False

# ======================================================
# MODELS
# ======================================================

class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ======================================================
# ROUTES
# ======================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>✅ Selenium MCP Server is live!</h2>"

@app.get("/mcp/ping")
async def ping():
    return {"status": "ok"}

@app.get("/mcp/debug")
async def debug():
    """Return diagnostic info."""
    version = get_chrome_version()
    exists = os.path.exists(CHROMEDRIVER_PATH)
    return {
        "chrome_binary": CHROME_BINARY,
        "chrome_exists": os.path.exists(CHROME_BINARY),
        "chrome_version": version,
        "chromedriver_path": CHROMEDRIVER_PATH,
        "chromedriver_exists": exists,
        "chromedriver_exec": os.access(CHROMEDRIVER_PATH, os.X_OK),
        "env_PATH": os.environ["PATH"],
    }

@app.post("/mcp/schema")
async def schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.5",
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
        if not os.path.exists(CHROMEDRIVER_PATH):
            download_driver(version)
        os.chmod(CHROMEDRIVER_PATH, 0o755)

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")

        log(f"✅ Using Chrome binary: {CHROME_BINARY}")
        log(f"✅ Using ChromeDriver: {CHROMEDRIVER_PATH}")

        # Force the Service to use our known driver
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        title = driver.title
        driver.quit()

        LAST_INVOCATION = f"Success: selenium_open_page → {url}"
        return {"result": {"url": url, "title": title}}

    except Exception as e:
        LAST_INVOCATION = f"Failed: {e}"
        return JSONResponse(
            status_code=500,
            content={"detail": f"500: Chrome could not start in current environment: {e}"},
        )

# ======================================================
# STARTUP
# ======================================================

if __name__ == "__main__":
    log("🚀 Starting Render-safe Selenium MCP Server...")
    ver = get_chrome_version()
    if ver:
        download_driver(ver)
    log(f"Chrome binary: {CHROME_BINARY}")
    log(f"Python runtime: {os.popen('python3 --version').read().strip()}")
    log(f"Binding to PORT={PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

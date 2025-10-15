from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import pyppeteer.chromium_downloader as chromium_downloader
import os
import time

app = FastAPI(title="Selenium MCP Server")

# -------------------------------
# Driver Initialization Function
# -------------------------------

def init_chrome_driver():
    """Initialize headless Chrome using downloaded Chromium and auto-installed ChromeDriver."""

    try:
        # Step 1: Locate Chromium binary (download if missing)
        chromium_executable = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_executable):
            print("[INFO] Chromium not found, downloading...")
            chromium_downloader.download_chromium()
            chromium_executable = chromium_downloader.chromium_executable()

        # Step 2: Ensure file is executable
        os.chmod(chromium_executable, 0o755)
        print(f"[INFO] Chromium binary ready: {chromium_executable}")

        # Step 3: Add Chromium folder to PATH (Render isolates /opt/render)
        chromium_dir = os.path.dirname(chromium_executable)
        os.environ["PATH"] = f"{chromium_dir}:{os.environ.get('PATH', '')}"
        print(f"[INFO] PATH updated: {os.environ['PATH']}")

        # Step 4: Ensure ChromeDriver installed
        driver_path = chromedriver_autoinstaller.install()
        print(f"[INFO] Using ChromeDriver at: {driver_path}")

        # Step 5: Configure headless Chrome options
        options = Options()
        options.binary_location = chromium_executable  # string path required
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")

        # Step 6: Launch Selenium driver
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        print("[INFO] Selenium Chrome driver started successfully.")
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise HTTPException(status_code=500, detail=f"Chrome could not start in current environment: {e}")

# -------------------------------
import os
import sys
import json
import shutil
import platform
import asyncio
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import chromedriver_autoinstaller
from pyppeteer import chromium_downloader

app = FastAPI(title="Selenium MCP Server")

driver = None
chromium_path = None


# -----------------------------------------------------------------------------
# INIT CHROME DRIVER
# -----------------------------------------------------------------------------
def init_chrome_driver():
    """Initialize a headless Chrome driver safely for Render environments."""
    global driver, chromium_path
    try:
        if driver:
            return driver

        print("[INFO] Checking for existing Chrome driver...")

        # Use pyppeteer to ensure a Chromium binary exists
        chromium_revision = chromium_downloader.REVISION
        chromium_exe = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_exe):
            print("[INFO] Chromium not found, downloading...")
            chromium_downloader.download_chromium()
        chromium_path = chromium_exe

        print(f"[INFO] Using Chromium binary at: {chromium_path}")

        # Install chromedriver automatically
        chromedriver_autoinstaller.install()

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.binary_location = chromium_path

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("[INFO] Chrome driver initialized successfully.")
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise HTTPException(status_code=500, detail=f"Chrome could not start in current environment: {e}")


# -----------------------------------------------------------------------------
# HEALTH CHECK ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/mcp/health")
def health_check():
    """Confirm Selenium driver availability."""
    global driver
    try:
        if driver is None:
            init_chrome_driver()
            return {"status": "ok", "message": "Selenium driver initialized"}
        else:
            _ = driver.title  # Touch driver
            return {"status": "ok", "message": "Selenium driver alive"}
    except Exception as e:
        return {"status": "down", "message": f"Driver not initialized: {str(e)}"}


# -----------------------------------------------------------------------------
# SCHEMA ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/mcp/schema")
def get_schema():
    """Return MCP-compliant schema for Agent Builder autodiscovery."""
    schema = {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless browser",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
            {
                "name": "selenium_click",
                "description": "Click an element by CSS selector",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"],
                },
            },
            {
                "name": "selenium_text",
                "description": "Get text content by CSS selector",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"],
                },
            },
            {
                "name": "selenium_screenshot",
                "description": "Save a PNG screenshot and return its path",
                "parameters": {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}},
                    "required": ["filename"],
                },
            },
        ],
    }
    return schema


# -----------------------------------------------------------------------------
# DEBUG ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/mcp/debug")
def debug_info():
    """Return detailed environment diagnostics."""
    global chromium_path
    info = {
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "env_PATH": os.getenv("PATH"),
        "chromium_executable": chromium_path,
        "chromium_exists": os.path.exists(chromium_path) if chromium_path else False,
        "chromium_permissions": (
            oct(os.stat(chromium_path).st_mode)[-3:]
            if chromium_path and os.path.exists(chromium_path)
            else None
        ),
    }
    return info


# -----------------------------------------------------------------------------
# INVOCATION ENDPOINT (MAIN MCP TOOL HANDLER)
# -----------------------------------------------------------------------------
class ToolRequest(BaseModel):
    tool: str
    arguments: dict


@app.post("/mcp/invoke")
def mcp_invoke(req: ToolRequest):
    """Execute a supported Selenium MCP tool."""
    global driver
    try:
        if driver is None:
            driver = init_chrome_driver()

        if req.tool == "selenium_open_page":
            url = req.arguments["url"]
            print(f"[INFO] Opening page: {url}")
            driver.get(url)
            title = driver.title
            return {"ok": True, "url": url, "title": title}

        elif req.tool == "selenium_click":
            sel = req.arguments["selector"]
            el = driver.find_element("css selector", sel)
            el.click()
            return {"ok": True, "selector": sel}

        elif req.tool == "selenium_text":
            sel = req.arguments["selector"]
            el = driver.find_element("css selector", sel)
            return {"ok": True, "selector": sel, "text": el.text}

        elif req.tool == "selenium_screenshot":
            fn = req.arguments["filename"]
            os.makedirs("./screenshots", exist_ok=True)
            path = os.path.join("./screenshots", fn)
            driver.save_screenshot(path)
            return {"ok": True, "filename": path}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {req.tool}")

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Recovered from Chrome failure: {e}")


# -----------------------------------------------------------------------------
# ROOT ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/")
def index():
    return {
        "status": "running",
        "service": "Selenium MCP",
        "schema": "/mcp/schema",
        "docs": "/docs",
    }


# -----------------------------------------------------------------------------
# ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Pre-warm Chromium download to avoid Render SSL timeout
    try:
        chromium_downloader.download_chromium()
    except Exception:
        pass

    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

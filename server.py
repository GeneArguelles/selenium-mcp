# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import os
import time
import shutil
import json

app = FastAPI()
_driver = None


@app.get("/")
def root():
    """Root route for quick Render diagnostics."""
    return {"status": "ok", "message": "Selenium MCP server running"}

def init_chrome_driver():
    """Initialize headless Chrome using chromedriver_autoinstaller and bundled Chromium."""
    import chromedriver_autoinstaller
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    import os
    import pyppeteer.chromium_downloader as chromium_downloader

    # Ensure a working Chrome binary is downloaded and ready
    chrome_path = chromium_downloader.chromium_executable()
    if not os.path.exists(chrome_path):
        print("[INFO] Downloading Chromium...")
        chromium_downloader.download_chromium()
    print(f"[INFO] Using Chromium binary at {chrome_path}")

    # Ensure the matching chromedriver is installed
    chromedriver_autoinstaller.install()

    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    print("[INFO] Selenium Chrome driver started successfully (Render-safe Chromium).")
    return driver

def get_driver():
    """Return a working Chrome driver, with automatic recovery if it fails."""
    global _driver

    def _ensure_alive(d):
        try:
            _ = d.title  # lightweight check
            return True
        except Exception:
            return False

    if _driver is None:
        print("[INFO] Creating new Chrome driver...")
        _driver = init_chrome_driver()
    else:
        if not _ensure_alive(_driver):
            print("[WARN] Chrome driver unresponsive. Restarting...")
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = init_chrome_driver()

    return _driver


@app.get("/mcp/schema")
def mcp_schema():
    """Advertise available tools to OpenAI's Agent Builder."""
    print("[INFO] Serving MCP schema")
    return {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless browser",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                },
            },
            {
                "name": "selenium_click",
                "description": "Click an element by CSS selector",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"]
                },
            },
            {
                "name": "selenium_text",
                "description": "Get text content by CSS selector",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"]
                },
            },
            {
                "name": "selenium_screenshot",
                "description": "Save a PNG screenshot to ./screenshots and return its path",
                "parameters": {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}},
                    "required": ["filename"]
                },
            }
        ]
    }


class InvokeBody(BaseModel):
    tool: str
    arguments: dict


@app.post("/mcp/invoke")
def mcp_invoke(body: InvokeBody):
    """Handle tool calls from the agent."""
    global _driver

    try:
        driver = get_driver()

        if body.tool == "selenium_open_page":
            url = body.arguments["url"]
            driver.get(url)
            time.sleep(1)
            return {"ok": True, "url": url}

        elif body.tool == "selenium_click":
            sel = body.arguments["selector"]
            element = driver.find_element(By.CSS_SELECTOR, sel)
            element.click()
            return {"ok": True, "clicked": sel}

        elif body.tool == "selenium_text":
            sel = body.arguments["selector"]
            text = driver.find_element(By.CSS_SELECTOR, sel).text
            return {"ok": True, "selector": sel, "text": text}

        elif body.tool == "selenium_screenshot":
            filename = body.arguments["filename"]
            os.makedirs("screenshots", exist_ok=True)
            path = os.path.join("screenshots", filename)
            driver.save_screenshot(path)
            return {"ok": True, "path": path}

        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {body.tool}")

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        try:
            if _driver:
                _driver.quit()
        except Exception:
            pass
        _driver = None
        raise HTTPException(status_code=500, detail=f"Recovered from Chrome failure: {e}")


@app.get("/mcp/health")
def mcp_health():
    """Lightweight health check endpoint."""
    global _driver
    try:
        if _driver is None:
            return {"status": "down", "message": "Driver not initialized"}

        _ = _driver.title
        return {"status": "ok", "message": "Selenium driver alive"}

    except Exception as e:
        return {"status": "down", "message": f"Driver error: {e}"}


print("[INFO] Selenium MCP Server started")

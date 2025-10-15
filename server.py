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
    """Initialize headless Chrome using undetected_chromedriver (cross-platform)."""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")

    # ✅ Do NOT force any binary location — let uc handle it automatically
    # It will download and use a compatible Chromium build for Render.

    try:
        driver = uc.Chrome(options=options, headless=True)
        print("[INFO] Chrome driver initialized successfully (auto-managed by undetected-chromedriver)")
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise HTTPException(status_code=500, detail=f"Chrome could not start in current environment: {e}")

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

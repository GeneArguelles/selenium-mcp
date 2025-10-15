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
        # Ensure a working Chromium binary exists
        chrome_path = chromium_downloader.chromium_executable()
        if not os.path.exists(chrome_path):
            print("[INFO] Chromium not found, downloading...")
            chromium_downloader.download_chromium()
        print(f"[INFO] Using Chromium binary at: {chrome_path}")

        # Ensure the matching ChromeDriver is installed
        chromedriver_autoinstaller.install()

        # Configure Selenium options
        options = Options()
        options.binary_location = chrome_path
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")

        # Launch Selenium with the new driver
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        print("[INFO] Selenium Chrome driver started successfully.")
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise HTTPException(status_code=500, detail=f"Chrome could not start in current environment: {e}")

# -------------------------------
# Pydantic Models
# -------------------------------
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# -------------------------------
# Tool Implementations
# -------------------------------
def selenium_open_page(url: str):
    print(f"[INFO] Opening page: {url}")
    driver = init_chrome_driver()
    try:
        driver.get(url)
        time.sleep(2)  # Allow time for page to load
        title = driver.title
        print(f"[INFO] Page loaded: {title}")
        return {"ok": True, "url": url, "title": title}
    except Exception as e:
        print(f"[ERROR] Failed to open page: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        driver.quit()
        print("[INFO] Driver closed successfully.")

# -------------------------------
# API Endpoints
# -------------------------------
@app.post("/mcp/invoke")
def invoke_tool(request: InvokeRequest):
    try:
        if request.tool == "selenium_open_page":
            url = request.arguments.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="Missing 'url' argument")
            return selenium_open_page(url)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool}")
    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        raise HTTPException(status_code=500, detail=f"Recovered from Chrome failure: {e}")

@app.get("/mcp/health")
def health_check():
    return {"status": "ok", "message": "Selenium driver alive"}

@app.get("/")
def root():
    return {"status": "running", "service": "Selenium MCP", "docs": "/docs"}

# -------------------------------
# Entry Point for Local Testing
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=10000)

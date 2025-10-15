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
        # Determine Chromium executable path
        chromium_dir = os.path.join(os.path.expanduser("~"), ".local/share/pyppeteer/local-chromium")
        chromium_executable = chromium_downloader.chromium_executable()
        if not os.path.exists(chromium_executable):
            print("[INFO] Chromium not found, downloading...")
            chromium_downloader.download_chromium()
            chromium_executable = chromium_downloader.chromium_executable()

        if not os.path.exists(chromium_executable):
            raise FileNotFoundError(f"Chromium executable not found at {chromium_executable}")

        print(f"[INFO] Using Chromium binary at: {chromium_executable}")

        # Install ChromeDriver automatically
        driver_path = chromedriver_autoinstaller.install()
        print(f"[INFO] Using ChromeDriver at: {driver_path}")

        # Configure Selenium Chrome Options
        options = Options()
        options.binary_location = chromium_executable  # ✅ direct string path
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1280,800")

        # Launch the ChromeDriver service explicitly with our installed driver
        service = Service(driver_path)
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

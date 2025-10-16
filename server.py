from fastapi import FastAPI
from pydantic import BaseModel
import os, platform, shutil, subprocess, json, tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_binary_auto  # auto installs chromedriver
from pyppeteer import chromium_downloader

app = FastAPI(title="Selenium MCP")

# -------------------------------------------------------
#  CHROME DRIVER INITIALIZER with Fallback
# -------------------------------------------------------
def init_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")

    # --- Priority 1: system chromium
    candidate_binaries = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    candidate_binaries = [p for p in candidate_binaries if p and os.path.exists(p)]

    # --- Priority 2: embedded fallback
    fallback_path = os.path.join(
        chromium_downloader.chromium_executable(),
    )
    if not os.path.exists(fallback_path):
        print("[INFO] Downloading fallback Chromium (pyppeteer)...")
        chromium_downloader.download_chromium()
    if os.path.exists(fallback_path):
        candidate_binaries.append(fallback_path)

    # choose first valid binary
    binary_path = next((p for p in candidate_binaries if os.path.exists(p)), None)
    if not binary_path:
        raise RuntimeError("No Chromium binary found anywhere.")

    chrome_options.binary_location = binary_path
    print(f"[INFO] Using Chrome binary: {binary_path}")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

# -------------------------------------------------------
#  MODELS
# -------------------------------------------------------
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# -------------------------------------------------------
#  MCP ENDPOINTS
# -------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Selenium MCP with fallback Chrome active"}

@app.get("/mcp/schema")
def schema():
    return {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a web page and return title + URL",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            }
        ]
    }

@app.post("/mcp/invoke")
def invoke(req: InvokeRequest):
    try:
        if req.tool == "selenium_open_page":
            driver = init_chrome_driver()
            driver.get(req.arguments["url"])
            title = driver.title
            driver.quit()
            return {"ok": True, "url": req.arguments["url"], "title": title}
        else:
            return {"error": f"Unknown tool {req.tool}"}
    except Exception as e:
        return {"detail": f"Recovered from Chrome failure: {e}"}

@app.get("/mcp/debug")
def debug():
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "path_env": os.getenv("PATH"),
        "which_chromium": shutil.which("chromium"),
        "which_chrome": shutil.which("google-chrome"),
        "which_chromedriver": shutil.which("chromedriver"),
        "fallback_chromium": chromium_downloader.chromium_executable(),
        "fallback_exists": os.path.exists(chromium_downloader.chromium_executable()),
    }

# ==========================================================
# server.py — Render-safe Selenium MCP Server with fallback
# ==========================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import subprocess
import shutil
from pathlib import Path
import sys
import os
import platform
import traceback

app = FastAPI(title="Selenium MCP Server")

# ----------------------------------------------------------
# Safe ChromeDriver and Chromium Fallback Initialization
# ----------------------------------------------------------
def init_chrome_driver():
    try:
        # Detect available ChromeDriver binary
        chromedriver_path = shutil.which("chromedriver")
        if not chromedriver_path:
            guess = Path("/opt/render/project/src/.venv/bin/chromedriver")
            if guess.exists():
                chromedriver_path = str(guess)
            else:
                print("[WARN] No chromedriver on PATH, Selenium will try manager fallback")

        # Detect Chromium binary
        chromium_candidates = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/opt/render/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome",
            "/tmp/chromium/chrome",
        ]
        chromium_binary = next((p for p in chromium_candidates if Path(p).exists()), None)

        if not chromium_binary:
            print("[WARN] No Chromium binary found, attempting to download headless fallback...")
            from pyppeteer.chromium_downloader import download_chromium, chromium_executable
            download_chromium()
            chromium_binary = chromium_executable()

        # Verify binary works
        try:
            result = subprocess.run([chromium_binary, "--version"], capture_output=True, text=True)
            print(f"[INFO] Using Chromium binary: {chromium_binary} → {result.stdout.strip()}")
        except Exception as e:
            print(f"[WARN] Failed to verify Chromium binary: {e}")

        chrome_options = Options()
        chrome_options.binary_location = chromium_binary
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")

        service = Service(chromedriver_path) if chromedriver_path else None
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("[INFO] ChromeDriver initialized successfully.")
        return driver

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] init_chrome_driver() failed: {e}\n{tb}")
        raise RuntimeError(f"Chrome could not start: {e}")

# ----------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------
class MCPInvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ----------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Selenium MCP Server running"}

# ----------------------------------------------------------
# Debug Environment Endpoint
# ----------------------------------------------------------
@app.get("/mcp/debug")
def debug():
    chromium_exec = Path("/opt/render/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome")
    relocated = Path("/tmp/chromium/chrome")
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
        "path_env": os.environ.get("PATH"),
        "chromium_exec": str(chromium_exec),
        "chrome_exists": chromium_exec.exists(),
        "relocated_path": str(relocated),
        "relocated_exists": relocated.exists(),
        "which_chromedriver": shutil.which("chromedriver"),
        "which_chrome": shutil.which("chrome"),
        "which_chromium": shutil.which("chromium"),
    }

# ----------------------------------------------------------
# Schema Endpoint for OpenAI Agent Builder Discovery
# ----------------------------------------------------------
@app.get("/mcp/schema")
def schema():
    return {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            }
        ]
    }

# ----------------------------------------------------------
# Invoke Endpoint — Core Selenium MCP Action
# ----------------------------------------------------------
@app.post("/mcp/invoke")
def invoke(req: MCPInvokeRequest):
    try:
        if req.tool == "selenium_open_page":
            driver = init_chrome_driver()
            driver.get(req.arguments["url"])
            title = driver.title
            driver.quit()
            return {"ok": True, "url": req.arguments["url"], "title": title}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {req.tool}")
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] Invocation failed: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Recovered from Chrome failure: {e}")

# ----------------------------------------------------------
# Run locally if executed directly
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting Selenium MCP Server...")
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

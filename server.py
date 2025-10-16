import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


app = FastAPI(title="Selenium MCP Server", version="2025-10-01")

# -------------------------------------------------------------------
# ✅ Add CORS Middleware for OpenAI Agent Builder Compatibility
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow any origin (Agent Builder UI)
    allow_credentials=True,
    allow_methods=["*"],          # GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Browser initialization
# -------------------------------------------------------------------
def init_chrome_driver():
    """Initialize ChromeDriver with safe Render-compatible options."""
    print("[INFO] Initializing Chrome driver...")

    # Define fallback search paths
    possible_chrome_paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/opt/render/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome",
        "/tmp/chromium/chrome",
    ]

    # Determine the first available binary
    chrome_binary = next((p for p in possible_chrome_paths if Path(p).exists()), None)
    if not chrome_binary:
        print("[WARN] No Chrome binary found — will rely on Selenium auto-managed driver.")
    else:
        print(f"[INFO] Using Chrome binary at: {chrome_binary}")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome startup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chrome could not start in current environment: {e}")


# -------------------------------------------------------------------
# MCP Tool Invocation Models
# -------------------------------------------------------------------
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict


# -------------------------------------------------------------------
# Core Endpoints
# -------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "running", "message": "Selenium MCP Server active"}


@app.get("/mcp/ping")
async def ping():
    return {"status": "ok"}


@app.get("/mcp/debug")
async def debug():
    """Expose diagnostic info to check Render sandbox state."""
    chromium_exec = Path("/opt/render/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome")
    relocated_path = Path("/tmp/chromium/chrome")

    debug_info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
        "path_env": os.environ.get("PATH"),
        "chromium_exec": str(chromium_exec),
        "chrome_exists": chromium_exec.exists(),
        "relocated_path": str(relocated_path) if relocated_path.exists() else None,
        "relocated_exists": relocated_path.exists(),
        "which_chromedriver": shutil.which("chromedriver"),
        "which_chrome": shutil.which("google-chrome"),
        "which_chromium": shutil.which("chromium"),
    }

    # Try to get version info if Chromium exists
    try:
        result = subprocess.run([str(chromium_exec), "--version"], capture_output=True, text=True, check=False)
        debug_info["chrome_version_output"] = result.stdout.strip()
        debug_info["chrome_exec_status"] = result.returncode
    except Exception as e:
        debug_info["chrome_exec_error"] = str(e)

    return debug_info


# -------------------------------------------------------------------
# MCP Schema — supports GET and POST (Agent Builder compatible)
# -------------------------------------------------------------------
@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema():
    schema = {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            },
        ],
    }
    return JSONResponse(content=schema)


# -------------------------------------------------------------------
# MCP Invoke — perform actions
# -------------------------------------------------------------------
@app.post("/mcp/invoke")
async def mcp_invoke(request: InvokeRequest):
    try:
        if request.tool == "selenium_open_page":
            url = request.arguments.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="Missing URL argument")

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"ok": True, "url": url, "title": title}

        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {request.tool}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        return {"detail": f"Recovered from Chrome failure: {e}"}

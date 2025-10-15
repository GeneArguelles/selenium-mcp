# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pyppeteer.chromium_downloader as chromium_downloader
import chromedriver_autoinstaller
import os
import time
import platform
import json

app = FastAPI()
_driver = None


# ================================================================
# INIT CHROME DRIVER — Render-safe, auto-recovers via pyppeteer
# ================================================================

def init_chrome_driver():
    """Initialize headless Chrome driver for Render sandbox (safe relocation version)."""
    import os, stat, shutil
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import pyppeteer.chromium_downloader as chromium_downloader
    import chromedriver_autoinstaller

    print("[INFO] Starting Chrome driver initialization...")

    # Step 1: Locate or download Chromium
    chromium_path = chromium_downloader.chromium_executable()
    if not os.path.exists(chromium_path):
        print("[WARN] Chromium not found — downloading fresh copy...")
        chromium_downloader.download_chromium()
        chromium_path = chromium_downloader.chromium_executable()
    print(f"[DEBUG] Original Chromium path: {chromium_path}")

    # Step 2: Copy to a guaranteed executable directory
    target_dir = "/tmp/chromium"
    os.makedirs(target_dir, exist_ok=True)
    relocated_path = os.path.join(target_dir, "chrome")

    try:
        shutil.copy2(chromium_path, relocated_path)
        os.chmod(relocated_path, 0o755)
        print(f"[INFO] Chromium relocated and chmodded: {relocated_path}")
    except Exception as e:
        print(f"[WARN] Could not relocate Chromium: {e}")
        relocated_path = chromium_path  # fallback

    # Step 3: Install matching ChromeDriver
    chromedriver_autoinstaller.install()

    # Step 4: Configure Selenium
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.binary_location = relocated_path  # << key line

    print(f"[INFO] Using Chromium binary at: {options.binary_location}")

    # Step 5: Start driver
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("[INFO] Chrome driver initialized successfully.")
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")

# ================================================================
# GET DRIVER — resilient wrapper
# ================================================================
def get_driver():
    """Return a live Chrome driver or restart if it crashed."""
    global _driver

    def _alive(d):
        try:
            _ = d.title
            return True
        except Exception:
            return False

    if _driver is None:
        print("[INFO] Creating new Chrome driver...")
        _driver = init_chrome_driver()
    elif not _alive(_driver):
        print("[WARN] Chrome driver unresponsive — restarting...")
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = init_chrome_driver()

    return _driver


# ================================================================
# FASTAPI ENDPOINTS
# ================================================================
@app.get("/")
def home():
    return {"status": "ok", "message": "Selenium MCP Server online"}


@app.get("/mcp/schema")
def mcp_schema():
    """Advertise available tools for OpenAI Agent Builder."""
    return {
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
                "description": "Save a PNG screenshot to ./screenshots and return its path",
                "parameters": {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}},
                    "required": ["filename"],
                },
            },
        ],
    }


class InvokeBody(BaseModel):
    tool: str
    arguments: dict


@app.post("/mcp/invoke")
def mcp_invoke(body: InvokeBody):
    """Handle tool calls from OpenAI Agent Builder."""
    global _driver
    try:
        driver = get_driver()

        if body.tool == "selenium_open_page":
            url = body.arguments["url"]
            print(f"[INFO] Opening page: {url}")
            driver.get(url)
            time.sleep(2)
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
    """Simple health endpoint to confirm Selenium is alive."""
    global _driver
    try:
        if _driver is None:
            return {"status": "down", "message": "Driver not initialized"}
        _ = _driver.title
        return {"status": "ok", "message": "Selenium driver alive"}
    except Exception as e:
        return {"status": "down", "message": f"Driver error: {e}"}


@app.get("/mcp/debug")
def mcp_debug():
    """Diagnostics for Render sandbox environment."""
    import traceback, subprocess, shutil, stat

    info = {}
    try:
        info["python_version"] = platform.python_version()
        info["platform"] = platform.platform()
        info["cwd"] = os.getcwd()
        info["home"] = os.environ.get("HOME")
        info["path_env"] = os.environ.get("PATH")

        # Locate Chromium
        try:
            chromium_exec = chromium_downloader.chromium_executable()
            info["chromium_exec"] = chromium_exec
            info["chrome_exists"] = os.path.exists(chromium_exec)
        except Exception as e:
            info["chromium_exec_error"] = str(e)
            chromium_exec = None

        # Relocate to /tmp if necessary
        relocated_path = "/tmp/chromium/chrome"
        try:
            if chromium_exec and os.path.exists(chromium_exec):
                os.makedirs("/tmp/chromium", exist_ok=True)
                shutil.copy2(chromium_exec, relocated_path)
                os.chmod(relocated_path, 0o755)
                info["relocated_path"] = relocated_path
                info["relocated_exists"] = os.path.exists(relocated_path)
            else:
                info["relocated_path"] = None
        except Exception as e:
            info["relocation_error"] = str(e)

        # Try executing the relocated binary
        try:
            result = subprocess.run(
                [relocated_path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            info["chrome_version_output"] = result.stdout.decode().strip()
            info["chrome_exec_status"] = result.returncode
        except Exception as e:
            info["chrome_exec_error"] = str(e)

        # Which binaries are visible
        import shutil
        info["which_chromium"] = shutil.which("chromium")
        info["which_chrome"] = shutil.which("chrome")
        info["which_google_chrome"] = shutil.which("google-chrome")
        info["which_chromedriver"] = shutil.which("chromedriver")

    except Exception:
        info["fatal_error"] = traceback.format_exc()

    return info

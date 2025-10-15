import os, shutil, subprocess, platform, traceback
from fastapi import FastAPI, Request
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pyppeteer.chromium_downloader as chromium_downloader
import chromedriver_autoinstaller

app = FastAPI(title="Selenium MCP Server")

# ---------- Driver init ----------
def init_chrome_driver():
    """Initialize headless Chrome in Render sandbox."""
    print("[INFO] Initializing Chrome driver...")

    # Locate / download Chromium
    chromium_path = chromium_downloader.chromium_executable()
    if not os.path.exists(chromium_path):
        chromium_downloader.download_chromium()
        chromium_path = chromium_downloader.chromium_executable()

    # Relocate to /tmp to make executable
    tmp_dir = "/tmp/chromium"
    os.makedirs(tmp_dir, exist_ok=True)
    relocated_path = os.path.join(tmp_dir, "chrome")
    if not os.path.exists(relocated_path):
        shutil.copy2(chromium_path, relocated_path)
        os.chmod(relocated_path, 0o755)

    # Verify Chromium runs
    result = subprocess.run(
        [relocated_path, "--version"], capture_output=True, text=True
    )
    print(f"[INFO] Using {result.stdout.strip()}")

    # Install ChromeDriver & locate
    chromedriver_autoinstaller.install()
    chromedriver_path = chromedriver_autoinstaller.get_chromedriver_path()
    print(f"[INFO] ChromeDriver path: {chromedriver_path}")

    # Selenium options
    options = Options()
    options.binary_location = relocated_path
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")

    # Explicitly start with verified paths
    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service, options=options)
        print("[INFO] ✅ ChromeDriver initialized successfully.")
        return driver
    except Exception as e:
        print(f"[ERROR] ❌ Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start: {e}")

# ---------- API Models ----------
class InvokePayload(BaseModel):
    tool: str
    arguments: dict

# ---------- Endpoints ----------
@app.get("/")
def root():
    return {"message": "Selenium MCP Server active."}

@app.post("/mcp/invoke")
def mcp_invoke(payload: InvokePayload):
    """Single-tool interface for Agent Builder."""
    try:
        if payload.tool == "selenium_open_page":
            url = payload.arguments.get("url")
            if not url:
                return {"detail": "Missing URL"}
            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"ok": True, "url": url, "title": title}
        return {"detail": f"Unknown tool: {payload.tool}"}
    except Exception as e:
        return {"detail": f"Recovered from Chrome failure: {e}"}

@app.get("/mcp/schema")
def mcp_schema():
    """Expose MCP schema for Agent Builder auto-discovery."""
    return {
        "version": "2025-10-01",
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in headless Chromium and return its title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }

@app.get("/mcp/debug")
def mcp_debug():
    """Expose environment diagnostics for Render sandbox."""
    info = {}
    try:
        info["python_version"] = platform.python_version()
        info["platform"] = platform.platform()
        info["cwd"] = os.getcwd()
        info["home"] = os.environ.get("HOME")
        info["path_env"] = os.environ.get("PATH")

        chromium_exec = chromium_downloader.chromium_executable()
        info["chromium_exec"] = chromium_exec
        info["chrome_exists"] = os.path.exists(chromium_exec)

        # Relocate check
        relocated_path = "/tmp/chromium/chrome"
        info["relocated_path"] = relocated_path
        info["relocated_exists"] = os.path.exists(relocated_path)

        # Version test
        try:
            result = subprocess.run(
                [relocated_path, "--version"], stdout=subprocess.PIPE, timeout=5
            )
            info["chrome_version_output"] = result.stdout.decode().strip()
        except Exception as e:
            info["chrome_version_error"] = str(e)

        import shutil
        info["which_chromium"] = shutil.which("chromium")
        info["which_chrome"] = shutil.which("chrome")
        info["which_google_chrome"] = shutil.which("google-chrome")
        info["which_chromedriver"] = shutil.which("chromedriver")
    except Exception:
        info["fatal_error"] = traceback.format_exc()
    return info

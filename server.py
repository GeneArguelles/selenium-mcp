import os
import time
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# ==========================================================
#  ENVIRONMENT INITIALIZATION
# ==========================================================
load_dotenv()
app = FastAPI(title="Selenium MCP Server")

PORT = int(os.getenv("PORT", "10000"))
CHROME_PATH = os.getenv("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
CHROME_VERSION = os.getenv("CHROME_VERSION", "120")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# ==========================================================
#  STARTUP LOGGING
# ==========================================================
print("==========================================================")
print("[INFO] Starting Selenium MCP Server...")
print(f"[INFO] Description: MCP server providing headless browser automation via Selenium.")
print(f"[INFO] Version: 1.0.0")
print(f"[INFO] Python Runtime: {os.getenv('PYTHON_VERSION', 'Unknown')}")
print(f"[INFO] Chrome Binary: {CHROME_PATH}")
print(f"[INFO] Chrome Version (env): {CHROME_VERSION}")
print(f"[INFO] DRY_RUN Mode: {DRY_RUN}")
print("==========================================================")


# ==========================================================
#  ROOT ENDPOINT
# ==========================================================
@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Selenium MCP Server is live.",
        "runtime": os.getenv("PYTHON_VERSION", "unknown"),
        "chrome_path": CHROME_PATH,
    }

@app.post("/")
def post_root():
    """
    Agent Builder root discovery endpoint.
    It tells the client where to find schema and invocation routes.
    """
    print("[INFO] POST / root discovery requested")
    return JSONResponse(
        content={
            "type": "mcp_server",
            "version": "2025-10-01",
            "endpoints": {
                "schema": "/mcp/schema",
                "invoke": "/mcp/invoke",
                "status": "/mcp/status"
            },
            "server_info": {
                "name": "Selenium",
                "description": "MCP server providing headless browser automation via Selenium.",
                "version": "1.0.0"
            }
        }
    )

# ==========================================================
#  MCP SCHEMA (GET + POST)
# ==========================================================
@app.get("/mcp/schema")
@app.post("/mcp/schema")
def get_schema():
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "name": "Selenium",
            "description": "Headless browser automation server using Selenium.",
            "version": "1.0.0"
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to open in the browser."
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
    }
    print("[INFO] Served strict /mcp/schema (Agent Builder tool-contract compliant)")
    return JSONResponse(content=schema)


# ==========================================================
#  MCP INVOKE (main handler)
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))
        tool = payload.get("tool")
        args = payload.get("arguments", {})
        url = args.get("url")

        if tool != "selenium_open_page":
            return JSONResponse(status_code=400, content={"error": f"Unknown tool '{tool}'"})

        if not url:
            return JSONResponse(status_code=400, content={"error": "Missing required argument: url"})

        print(f"[INFO] Invoking selenium_open_page for: {url}")

        # DRY RUN MODE (for MCP/Agent Builder validation)
        if DRY_RUN:
            print("[INFO] DRY_RUN active — returning simulated response.")
            return JSONResponse(content={"result": {"url": url, "title": "Simulated Title (DRY_RUN)"}})

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.binary_location = CHROME_PATH

        # Try dynamic ChromeDriver installation (matching version)
        print(f"[INFO] Attempting to install ChromeDriver matching version {CHROME_VERSION}...")
        try:
            service = Service(ChromeDriverManager(version=CHROME_VERSION).install())
        except Exception as e:
            print(f"[WARN] webdriver-manager failed: {e}")
            print("[INFO] Falling back to manual ChromeDriver 120 download...")
            os.system(
                "mkdir -p /tmp/chromedriver && cd /tmp/chromedriver && "
                "curl -O https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.18/linux64/chromedriver-linux64.zip && "
                "unzip -o chromedriver-linux64.zip && mv chromedriver-linux64/chromedriver ."
            )
            service = Service("/tmp/chromedriver/chromedriver")

        # Launch browser
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        title = driver.title
        driver.quit()

        print(f"[SUCCESS] Opened {url} — Title: {title}")
        return JSONResponse(content={"result": {"url": url, "title": title}})

    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON payload received."})
    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse(status_code=500, content={"detail": f"500: Chrome could not start in current environment: {e}"})


# ==========================================================
#  STARTUP DELAY (Render cold-start safety)
# ==========================================================
@app.on_event("startup")
def startup_event():
    print("[INFO] Performing cold-start warmup delay...")
    time.sleep(3)
    print("[INFO] Selenium MCP startup complete.")


# ==========================================================
#  MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Launching MCP Server on port {PORT} ...")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT)

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv

# ==========================================================
# 1️⃣ LOAD ENVIRONMENT VARIABLES
# ==========================================================
load_dotenv()

app = FastAPI(title="Selenium MCP Server", version="1.0.0")

PORT = int(os.getenv("PORT", 10000))
CHROME_PATH = os.getenv("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/tmp/chromedriver/chromedriver")
CHROME_VERSION = os.getenv("CHROME_VERSION", "120")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

print("==========================================================")
print("[INFO] Starting Selenium MCP Server...")
print(f"[INFO] Description: MCP server providing headless browser automation via Selenium.")
print(f"[INFO] Version: 1.0.0")
print(f"[INFO] Python Runtime: {os.sys.version.split()[0]}")
print(f"[INFO] Chrome Binary: {CHROME_PATH}")
print(f"[INFO] Chrome Version (env): {CHROME_VERSION}")
print(f"[INFO] ChromeDriver Path: {CHROMEDRIVER_PATH}")
print(f"[INFO] DRY_RUN Mode: {DRY_RUN}")
print("==========================================================")

# ==========================================================
# 2️⃣ ROOT ENDPOINT (GET + POST)
# ==========================================================
@app.get("/")
def get_root():
    """Simple health check for MCP server."""
    return JSONResponse(
        content={
            "status": "running",
            "message": "Selenium MCP Server is live.",
            "runtime": os.sys.version.split()[0],
            "chrome_path": CHROME_PATH,
        }
    )


@app.post("/")
def post_root():
    """Root discovery endpoint required by Agent Builder."""
    print("[INFO] POST / root discovery requested")
    return JSONResponse(
        content={
            "type": "mcp",
            "version": "2025-10-01",
            "endpoints": {
                "schema": "/mcp/schema",
                "invoke": "/mcp/invoke",
                "status": "/mcp/status",
            },
            "server_info": {
                "name": "Selenium",
                "description": "Headless browser automation server using Selenium.",
                "version": "1.0.0",
            },
        }
    )

# ==========================================================
# 3️⃣ MCP SCHEMA (GET + POST) — STRICT AGENT BUILDER COMPLIANT
# ==========================================================
@app.get("/mcp/schema")
@app.post("/mcp/schema")
def get_schema():
    """Defines the MCP server schema (OpenAI 2025-10 compliant)."""
    schema = {
        "version": "2025-10-01",
        "type": "mcp",
        "server_info": {
            "name": "Selenium",
            "description": "Headless browser automation server using Selenium.",
            "version": "1.0.0",
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
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

    print("[INFO] Served /mcp/schema (OpenAI MCP 2025-10 compliant)")
    return JSONResponse(content=schema, media_type="application/json")

# ==========================================================
# 4️⃣ MCP INVOKE
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """Handles incoming MCP tool invocation requests."""
    payload = await request.json()
    print(f"[INFO] Invocation payload received:\n{json.dumps(payload, indent=2)}")

    tool = payload.get("tool")
    args = payload.get("arguments", {})

    if tool == "selenium_open_page":
        url = args.get("url")
        if not url:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing 'url' argument for selenium_open_page."}
            )

        if DRY_RUN:
            print(f"[DRY RUN] Would open URL: {url}")
            return JSONResponse(content={"result": {"url": url, "title": "DRY_RUN"}})

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = CHROME_PATH

        service = Service(CHROMEDRIVER_PATH)

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            title = driver.title
            driver.quit()
            print(f"[INFO] Page opened successfully: {url} → Title: {title}")
            return JSONResponse(content={"result": {"url": url, "title": title}})
        except Exception as e:
            print(f"[ERROR] Chrome execution failed: {e}")
            return JSONResponse(status_code=500, content={"detail": f"Chrome could not start: {e}"})
    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown tool '{tool}'"})

# ==========================================================
# 5️⃣ STATUS ENDPOINT
# ==========================================================
@app.get("/mcp/status")
def get_status():
    """Quick status check for Agent Builder or monitoring probes."""
    return JSONResponse(
        content={
            "status": "ok",
            "chrome_path": CHROME_PATH,
            "driver_path": CHROMEDRIVER_PATH
        }
    )

# ==========================================================
# 6️⃣ MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Launching MCP Server on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

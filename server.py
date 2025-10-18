# ==========================================================
# Selenium MCP Server — Render Ready (Audited + Production)
# ==========================================================
import os
import time
import platform
import random
import string
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================================================
# Environment & Constants
# ==========================================================
APP_START_TIME = time.time()
SERVER_NAME = "Selenium"
SERVER_DESC = "MCP server providing headless browser automation via Selenium."

#
# Chrome Binary Validation (Render + Local fallback)
# ----------------------------------------------------------
# Detects Chrome binary for both Render and local macOS development.
# Provides explicit diagnostics to confirm mode and path.
#
CHROME_BINARY = os.getenv("CHROME_BINARY")
DEFAULT_RENDER_CHROME = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if not CHROME_BINARY:
    if os.path.exists(DEFAULT_RENDER_CHROME):
        CHROME_BINARY = DEFAULT_RENDER_CHROME
        print(f"[INFO] ✅ Chrome binary confirmed: {CHROME_BINARY} (Render mode)")
    elif os.path.exists(LOCAL_CHROME_PATH):
        CHROME_BINARY = LOCAL_CHROME_PATH
        print(f"[INFO] ✅ Chrome binary confirmed: {CHROME_BINARY} (Local mode)")
    else:
        CHROME_BINARY = DEFAULT_RENDER_CHROME
        print(f"[WARN] ⚠️ Chrome binary not found, falling back to {CHROME_BINARY}")
else:
    print(f"[INFO] ✅ Chrome binary confirmed from .env: {CHROME_BINARY}")

# ==========================================================
# FastAPI Initialization + CORS
# ==========================================================
app = FastAPI(title="Selenium MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==========================================================
# Health & Diagnostics Endpoint
# ==========================================================
@app.get("/health")
def health_check():
    uptime = round(time.time() - APP_START_TIME, 2)
    phase = "ready"
    chrome_ok = os.path.exists(CHROME_BINARY)
    return {
        "status": "healthy" if chrome_ok else "unhealthy",
        "phase": phase,
        "uptime_seconds": uptime,
        "chrome_path": CHROME_BINARY,
    }

# ==========================================================
# MCP Models
# ==========================================================
class SchemaResponse(BaseModel):
    version: str
    type: str
    server_info: dict
    tools: list


class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ==========================================================
# /mcp/schema — Exposes tool definitions
# ==========================================================
@app.get("/mcp/schema")
def get_schema():
    print("[INFO] Served /mcp/schema (explicit schema endpoint)")
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "type": "mcp_server",
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": "1.0.0",
            "runtime": platform.python_version(),
            "capabilities": {
                "invocation": True,
                "streaming": False,
                "multi_tool": False,
            },
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }
    return JSONResponse(content=schema)

# ==========================================================
# /mcp/invoke — Executes a Selenium automation command
# ==========================================================
@app.post("/mcp/invoke")
def invoke_tool(req: InvokeRequest):
    print(f"[INFO] Invoked tool: {req.tool}")

    if req.tool == "selenium_open_page":
        url = req.arguments.get("url")
        if not url:
            return JSONResponse(status_code=400, content={"error": "Missing URL argument"})

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = CHROME_BINARY

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"result": f"Opened {url}", "title": title}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return JSONResponse(status_code=400, content={"error": f"Unknown tool: {req.tool}"})

# ==========================================================
# / — Root Manifest (Self-contained for Agent Builder)
# ==========================================================
@app.api_route("/", methods=["GET", "POST"])
def root_manifest():
    """
    Root manifest for OpenAI Agent Builder discovery.
    Returns complete MCP definition with inline tools.
    """
    print("[INFO] Served root manifest for Agent Builder (self-contained)")

    manifest = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "type": "mcp_server",
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": "1.0.0",
            "runtime": platform.python_version(),
            "capabilities": {
                "invocation": True,
                "streaming": False,
                "multi_tool": False,
            },
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    }

    return JSONResponse(content=manifest)

# ==========================================================
# /live — Alias Endpoint (Cache-buster for Agent Builder)
# ==========================================================
@app.get("/live")
def live_check():
    """
    /live — Alias endpoint to force Agent Builder re-handshake.
    Returns a randomized cache-busting manifest URL to bypass stale schema.
    """
    nonce = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    print(f"[INFO] Served /live alias — cache-buster nonce={nonce}")
    return JSONResponse(
        content={
            "status": "live",
            "manifest_refresh": True,
            "nonce": nonce,
            "manifest_url": f"https://selenium-mcp.onrender.com/?v={nonce}",
        }
    )

# ==========================================================
# Local Execution Entry (Render uses start.sh)
# ==========================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

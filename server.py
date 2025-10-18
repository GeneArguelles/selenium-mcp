# ==========================================================
# server.py — Selenium MCP Server (Render + Local Ready)
# ==========================================================

import os
import platform
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# ==========================================================
# Environment Setup
# ==========================================================
load_dotenv()

APP_START_TIME = time.time()

app = FastAPI(title="Selenium MCP Server")

# Enable full CORS for Agent Builder / browser tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_NAME = os.getenv("SERVER_NAME", "Selenium")
SERVER_DESC = os.getenv(
    "SERVER_DESC", "MCP server providing headless browser automation via Selenium."
)
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"

# ==========================================================
# Chrome Binary Validation (Render + Local fallback)
# ==========================================================
if LOCAL_MODE:
    CHROME_BINARY = os.getenv(
        "LOCAL_CHROME_BINARY",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    CHROMEDRIVER_PATH = os.getenv(
        "LOCAL_CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver"
    )
else:
    CHROME_BINARY = os.getenv(
        "CHROME_BINARY",
        "/opt/render/project/src/.local/chrome/chrome-linux/chrome",
    )
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "./chromedriver/chromedriver")

# Validate Chrome binary presence
if not os.path.exists(CHROME_BINARY):
    print(f"[WARN] Chrome binary not found at {CHROME_BINARY}. Attempting fallback...")
    fallback_path = "/usr/bin/google-chrome"
    if os.path.exists(fallback_path):
        CHROME_BINARY = fallback_path
        print(f"[INFO] ✅ Using fallback Chrome binary: {CHROME_BINARY}")
    else:
        print(f"[ERROR] ❌ No valid Chrome binary found.")
else:
    print(f"[INFO] ✅ Chrome binary confirmed: {CHROME_BINARY}")

# ==========================================================
# Health and Diagnostics
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
# Root Manifest (GET + POST for Agent Builder discovery)
# ==========================================================
from fastapi.responses import JSONResponse

@app.api_route("/", methods=["GET", "POST"])
def root_manifest():
    """
    Root manifest for OpenAI Agent Builder (supports both GET and POST).
    """
    print("[INFO] Served root manifest at /")
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
        # ✅ Explicit Agent Builder handshake requirements
        "schema_url": "/mcp/schema",
        "tools": []  # must exist (even empty)
    }
    return JSONResponse(content=manifest)


# ==========================================================
# Root Manifest (required for MCP discovery)
# ==========================================================
@app.get("/")
def root_manifest():
    """
    Root manifest for OpenAI Agent Builder (MCP discovery).
    """
    print("[INFO] Served root manifest at /")
    return {
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
        "endpoints": {
            "schema": "/mcp/schema",
            "invoke": "/mcp/invoke",
            "health": "/health"
        }
    }


# ==========================================================
# MCP Schema + Invocation Models 
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
# MCP Schema Endpoint (GET/POST/OPTIONS, Builder + CORS safe)
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "OPTIONS"])
def mcp_schema():
    """
    Return the MCP tool schema for this Selenium service.

    We explicitly return JSON with permissive CORS headers and identity encoding
    to satisfy Agent Builder’s fetch (no gzip assumptions).
    """
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
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"],
                },
            }
        ],
    }

    # CORS + encoding headers for Agent Builder compatibility
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Content-Type": "application/json; charset=utf-8",
        "Content-Encoding": "identity",
    }

    # Short-circuit OPTIONS preflight
    if "OPTIONS" == os.getenv("REQUEST_METHOD", "").upper():
        return JSONResponse(status_code=204, content=None, headers=headers)

    print("[INFO] Served /mcp/schema (Agent Builder spec compliant)")
    return JSONResponse(content=schema, headers=headers)


# ==========================================================
# MCP Schema Endpoint (supports GET, POST, OPTIONS)
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "OPTIONS"])
def get_schema():
    """
    Return the MCP tool schema for this Selenium service.
    Fully CORS- and Agent Builder–compatible.
    """
    print("[INFO] Served /mcp/schema for Selenium (Agent Builder spec compliant)")

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

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    if app.debug:
        print("[DEBUG] OPTIONS preflight handled for /mcp/schema")

    return JSONResponse(content=schema, headers=headers)

# ==========================================================
# Selenium Tool Implementation
# ==========================================================
@app.post("/mcp/invoke")
def invoke_tool(request: InvokeRequest):
    """
    Execute a tool (e.g., selenium_open_page) via Selenium.
    """
    if request.tool == "selenium_open_page":
        url = request.arguments.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL argument.")

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        try:
            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"result": f"Opened {url}", "title": title}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chrome could not start: {e}")

    raise HTTPException(status_code=404, detail=f"Unknown tool: {request.tool}")

# ==========================================================
# Startup Info
# ==========================================================
@app.on_event("startup")
def on_startup():
    print("==========================================================")
    print("[INFO] Starting Selenium MCP Server...")
    print(f"[INFO] Description: {SERVER_DESC}")
    print(f"[INFO] Version: 1.0.0")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_BINARY}")
    print(f"[INFO] ChromeDriver Path: {CHROMEDRIVER_PATH}")
    print("==========================================================")
    print("[INFO] Selenium MCP startup complete.")

# ==========================================================
# Uvicorn Entrypoint
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)


# ==========================================================
# Entry Point for Render / Local Run
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "10000"))
    print(f"[INFO] 🚀 Launching Uvicorn server on port {port}...")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )

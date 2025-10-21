#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server (v2025.10.20b)
# ==========================================================
# Provides headless browser automation endpoints for OpenAI
# Agent Builder via the Model Context Protocol (MCP).
# ==========================================================

import os
import time
import platform
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================================================
# Environment Variable Setup (Render + Local)
# ==========================================================
RENDER_CHROME_PATH = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"

SERVER_NAME = os.getenv("SERVER_NAME", "Selenium")
SERVER_DESC = os.getenv("SERVER_DESC", "MCP server providing headless browser automation via Selenium.")
CHROME_BINARY = os.getenv("CHROME_BINARY", RENDER_CHROME_PATH)

# ==========================================================
# Globals
# ==========================================================
SERVER_NAME = "Selenium"
SERVER_DESC = "MCP server providing headless browser automation via Selenium."
APP_START_TIME = time.time()

# ==========================================================
# Chrome Binary Resolver (Render vs Local)
# ==========================================================
RENDER_CHROME_PATH = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CHROME_BINARY = (
    RENDER_CHROME_PATH if os.path.exists(RENDER_CHROME_PATH) else LOCAL_CHROME_PATH
)
print(f"[INFO] Chrome binary resolved as: {CHROME_BINARY}")

# ==========================================================
# FastAPI Init + CORS
# ==========================================================
app = FastAPI(title=f"{SERVER_NAME} MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://chat.openai.com", "https://builder.openai.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# ==========================================================
# Unified Schema Builder (used by /, /live, /mcp/schema)
# ==========================================================
def build_agentbuilder_schema():
    """Unified MCP-compatible schema for Agent Builder and validators."""
    return {
        "version": "2025-10-02",
	"mcp_version": "2025-10-20",
        "type": "mcp_server",
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": "1.0.0",
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False,
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

# ==========================================================
# Root Schema (Agent Builder entry)
# ==========================================================
@app.api_route("/", methods=["GET", "POST", "HEAD", "OPTIONS"])
def root_schema():
    print("[INFO] Served unified root schema")
    schema = build_agentbuilder_schema()
    return JSONResponse(content=schema)


# ==========================================================
# Versioned /live endpoint (Final hybrid for Agent Builder)
# ==========================================================
from fastapi.responses import JSONResponse

@app.api_route("/v20251020/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
def versioned_live_manifest():
    """
    Strict MCP-compliant manifest for OpenAI Agent Builder.
    """
    print("[INFO] Served /v20251020/live unified schema (strict MCP)")

    manifest = {
        "type": "mcp_server",
        "version": "2025-10-20",
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": "1.0.0",
            "runtime": platform.python_version(),
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
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            }
        ]
    }

    response = JSONResponse(
        content=manifest,
        media_type="application/json; charset=utf-8"
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ==========================================================
# Versioned /live endpoint (cache-bypass for Agent Builder)
# ==========================================================
@app.api_route("/v20251020/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
def versioned_live():
    """
    Versioned cache-bypass alias — ensures OpenAI Agent Builder sees a fresh schema.
    Mirrors /mcp/schema exactly.
    """
    print("[INFO] Served /v20251020/live unified schema (cache-bypass)")
    response = JSONResponse(content=unified_manifest())
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ==========================================================
# Backward compatibility redirect: /live → /v20251020/live
# ==========================================================
@app.api_route("/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def redirect_live_to_versioned():
    """Redirect old /live calls to the current versioned endpoint."""
    from fastapi.responses import RedirectResponse
    print("[INFO] Redirected /live → /v20251020/live")
    return RedirectResponse(url="/v20251020/live", status_code=307)


# ==========================================================
# /mcp/schema — Strict schema endpoint for validators
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "OPTIONS"])
def schema_endpoint():
    print("[INFO] Served /mcp/schema")
    schema = build_agentbuilder_schema()
    return JSONResponse(content=schema)

# ==========================================================
# /health — Detailed runtime probe
# ==========================================================
@app.get("/health")
def health_check():
    uptime = round(time.time() - APP_START_TIME, 2)
    chrome_ok = os.path.exists(CHROME_BINARY)
    return {
        "status": "healthy" if chrome_ok else "unhealthy",
        "phase": "ready" if chrome_ok else "init",
        "uptime_seconds": uptime,
        "chrome_path": CHROME_BINARY,
    }

# ==========================================================
# /mcp/invoke — Tool execution
# ==========================================================
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

@app.post("/mcp/invoke")
def invoke_tool(req: InvokeRequest):
    print(f"[INFO] Invoked tool: {req.tool}")
    if req.tool == "selenium_open_page":
        url = req.arguments.get("url")
        if not url:
            return JSONResponse(
                content={"error": "Missing 'url' argument."}, status_code=400
            )

        chrome_opts = Options()
        chrome_opts.add_argument("--headless")
        chrome_opts.add_argument("--disable-gpu")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.binary_location = CHROME_BINARY

        try:
            with webdriver.Chrome(options=chrome_opts) as driver:
                driver.get(url)
                title = driver.title
            return {"result": f"Opened {url}", "title": title}
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
    else:
        return JSONResponse(content={"error": f"Unknown tool: {req.tool}"}, status_code=400)

# ==========================================================
# Diagnostics
# ==========================================================
@app.options("/{full_path:path}")
def preflight(full_path: str):
    return JSONResponse(content={"status": "ok", "path": full_path})

@app.on_event("startup")
def startup_banner():
    print("[INFO] Starting Selenium MCP Server...")
    print(f"[INFO] Description: {SERVER_DESC}")
    print("[INFO] Version: 1.0.0")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_BINARY}")
    print("[INFO] ChromeDriver Path: ./chromedriver/chromedriver")
    print("==========================================================")
    print("[INFO] Selenium MCP startup complete.")

# ==========================================================
# Local execution entry point
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print("[INFO] Launching Uvicorn directly on port 10000...")
    uvicorn.run(app, host="0.0.0.0", port=10000)

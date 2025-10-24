# server.py
# ==========================================================
# Selenium MCP — Headless Browser Automation (FastAPI MCP)
# Version: v20251024-FULL
# Author: Gene Arguelles, LLC
# ==========================================================

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

# ----------------------------------------------------------
# Imports and FastAPI app setup
# ----------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to OpenAI IPs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------
# FastAPI App Init
# ----------------------------------------------------------
app = FastAPI()
MCP_VERSION = "v20251024c"
SERVER_NAME = "Selenium MCP"
SERVER_DESC = "Headless browser automation tools for OpenAI Agent Builder."
CHROME_BINARY = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"

# ----------------------------------------------------------
# Root manifest endpoint (for OpenAI Agent Builder)
# ----------------------------------------------------------
@app.get("/")
def root_manifest():
    return {
        "type": "manifest",
        "name": SERVER_NAME,
        "description": SERVER_DESC,
        "version": MCP_VERSION
    }

# ----------------------------------------------------------
# Health Check — Required for Render Liveness Check
# ----------------------------------------------------------
@app.get("/health")
def health_check():
    """
    Lightweight liveness check used by Render platform
    """
    return {"status": "ok"}

# ----------------------------------------------------------
# Schema Tool List (strict MCP format)
# ----------------------------------------------------------
MCP_TOOLS_LIST = [
    {
        "name": "selenium_open_page",
        "description": "Open a URL in a headless Chrome browser and return the page title.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    }
]

TOOL_EXECUTION_MAP = {
    "selenium_open_page": "handle_open_page"
}

# ----------------------------------------------------------
# Invocation Schema Input Model
# ----------------------------------------------------------
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict | None = None

# ==========================================================
# Root Manifest (for MCP discovery)
# ==========================================================
@app.get("/")
def root_manifest(request: Request):
    return {
        "type": "mcp_server",
        "mcp_version": MCP_VERSION,
        "version": MCP_VERSION,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": MCP_VERSION,
        },
        "endpoints": {
            "schema": f"{request.base_url}mcp/schema",
            "live": f"{request.base_url}live"
        }
    }

# ----------------------------------------------------------
# POST Root — Return manifest (for Agent Builder)
# ----------------------------------------------------------
@app.post("/")
def post_root_manifest(request: Request):
    return {
        "type": "mcp_server",
        "mcp_version": MCP_VERSION,
        "version": MCP_VERSION,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": MCP_VERSION,
        },
        "endpoints": {
            "schema": f"{request.base_url}mcp/schema",
            "live": f"{request.base_url}live",
        },
    }

# ----------------------------------------------------------
# Live Check — Lightweight Ping
# ----------------------------------------------------------
@app.get("/live")
def live():
    return {"status": "live", "version": MCP_VERSION}

# ----------------------------------------------------------
# MCP Schema — Exposes MCP_TOOLS_LIST in strict format
# ----------------------------------------------------------
@app.get("/mcp/schema")
def get_schema():
    return {
        "type": "mcp_server",
        "mcp_version": MCP_VERSION,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": MCP_VERSION,
            "runtime": os.getenv("PYTHON_VERSION", "3.11.9")
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False
        },
        "tools": MCP_TOOLS_LIST
    }

@app.post("/")
def post_root_manifest(request: Request):
    return root_manifest(request)

# ----------------------------------------------------------
# MCP POST fallback
# ----------------------------------------------------------
@app.post("/mcp/schema")
def post_schema():
    """
    Graceful POST fallback for schema endpoint.
    Agent Builder or other clients may probe via POST.
    """
    return get_schema()

# ----------------------------------------------------------
# MCP Invocation Endpoint
# ----------------------------------------------------------
@app.post("/mcp/invoke")
async def invoke_tool(req: InvokeRequest):
    tool = req.tool
    args = req.arguments or {}

    print(f"[INFO] Tool requested: {tool}")
    handler_name = TOOL_EXECUTION_MAP.get(tool)

    if not handler_name:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool}")

    handler_func = globals().get(handler_name)
    if not callable(handler_func):
        raise HTTPException(status_code=500, detail="Handler not callable.")

    try:
        result = await handler_func(args)
        return {"tool": tool, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------
# Tool Handler: selenium_open_page
# ----------------------------------------------------------
async def handle_open_page(args: dict):
    url = args.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' argument.")

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
        return {"url": url, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Selenium error: {e}")

# ----------------------------------------------------------
# Local Run Entrypoint (for local testing only)
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Launching MCP Server on port 10000 (version={MCP_VERSION})")
    uvicorn.run(app, host="0.0.0.0", port=10000)

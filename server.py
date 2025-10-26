# server.py
# ==========================================================
# Selenium MCP — Headless Browser Automation (FastAPI MCP)
# Version: v20251024-FULL
# Author: Gene Arguelles, LLC
# ==========================================================

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================================================
# Failsafe: guarantee MCP_VERSION always has a value at import time
# ==========================================================
import os, datetime

if "MCP_VERSION" not in globals() or not globals().get("MCP_VERSION"):
    # try environment first, else auto-generate daily version tag
    MCP_VERSION = os.getenv(
        "MCP_VERSION",
        f"v{datetime.date.today().strftime('%Y%m%d')}a"
    )
    print(f"[BOOT] MCP_VERSION pre-initialized as {MCP_VERSION}")

# ----------------------------------------------------------
# Imports and FastAPI app setup
# ----------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# Serve static assets (like logo.png)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to OpenAI IPs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# Failsafe: Ensure MCP_VERSION always initialized at import
# ==========================================================
MCP_VERSION = globals().get("MCP_VERSION") or os.getenv("MCP_VERSION") or "v20251024c"

# ==========================================================
# Constants and Global Declarations
# ==========================================================
MCP_VERSION = "v20251024c"
SERVER_NAME = "Selenium MCP"
SERVER_DESC = "Headless browser automation tools for OpenAI Agent Builder."
CHROME_BINARY = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
BASE_URL = os.getenv("BASE_URL", "https://selenium-mcp.onrender.com")

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
# MCP Manifest Endpoint (GET + POST)
# ----------------------------------------------------------
MCP_MANIFEST = {
    "type": "mcp_server",
    "schema_version": "v1",
    "name_for_human": SERVER_NAME,
    "name_for_model": "selenium",
    "description_for_human": SERVER_DESC,
    "description_for_model": "MCP server exposing Selenium tools: open_page, click, text, screenshot.",
    "auth": {"type": "none"},
    "api": {"type": "json", "url": f"{BASE_URL}/mcp/schema"},
    "logo_url": f"{BASE_URL}/static/logo.png",
    "contact_email": "youremail@example.com",
    "legal_info_url": f"{BASE_URL}/legal",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full URL of the page to open (including https://)."
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "selenium_click",
                "description": "Click an element on the page using a CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "The CSS selector for the element to click."
                        }
                    },
                    "required": ["selector"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "selenium_screenshot",
                "description": "Take a screenshot and save it to a file. Returns the local path to the screenshot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The desired filename (with .png extension) to save the screenshot."
                        }
                    },
                    "required": ["filename"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "selenium_get_text",
                "description": "Retrieve visible text content from the page using a CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "The CSS selector for the element to extract text from."
                        }
                    },
                    "required": ["selector"]
                }
            }
        }
    ],
}

@app.get("/mcp/manifest")
@app.post("/mcp/manifest")
async def get_manifest(request: Request):
    print(f"[INFO] /mcp/manifest served successfully ({len(MCP_MANIFEST['tools'])} tools)")
    return JSONResponse(content=MCP_MANIFEST)

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
# MCP_TOOLS_LIST (Strict OpenAI Function Schema)
# ----------------------------------------------------------
MCP_TOOLS_LIST = [
    {
        "type": "function",
        "function": {
            "name": "selenium_open_page",
            "description": "Open a URL in a headless Chrome browser and return the page title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the page to open (including https://)."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "selenium_click",
            "description": "Click an element on the page using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "The CSS selector for the element to click."
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "selenium_screenshot",
            "description": "Take a screenshot and save it to a file. Returns the local path to the screenshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The desired filename (with .png extension) to save the screenshot."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "selenium_get_text",
            "description": "Retrieve visible text content from the page using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "The CSS selector for the element to extract text from."
                    }
                },
                "required": ["selector"]
            }
        }
    }
]

@app.post("/mcp/schema")
def serve_adaptive_schema(request: Request):
    client_ua = request.headers.get("User-Agent", "unknown")
    print(f"[SCHEMA] Request from: {client_ua}")
    return {
        "version": MCP_VERSION,
        "tools": MCP_TOOLS_LIST
    }

TOOL_EXECUTION_MAP = {
    "selenium_open_page": "handle_open_page"
}


# ==========================================================
# OpenAI MCP Manifest (Agent Builder discovery compatible)
# ==========================================================
@app.get("/mcp/manifest")
def serve_manifest():
    """
    Always-safe manifest route for OpenAI Agent Builder discovery.
    Never throws; logs detailed errors to Render console.
    """
    from fastapi.responses import JSONResponse

    try:
        tools = MCP_TOOLS_LIST if "MCP_TOOLS_LIST" in globals() else []
        manifest = {
            "type": "mcp_server",
            "schema_version": "v1",
            "name_for_human": "Selenium MCP",
            "name_for_model": "selenium",
            "description_for_human": (
                "Headless browser automation tools for OpenAI Agent Builder. "
                "Provides Selenium-based methods for opening pages, clicking elements, "
                "extracting text, and taking screenshots."
            ),
            "description_for_model": (
                "MCP server exposing Selenium tools: open_page, click, text, screenshot."
            ),
            "auth": {"type": "none"},
            "api": {
                "type": "json",
                "url": "https://selenium-mcp.onrender.com/mcp/schema"
            },
            "logo_url": "https://selenium-mcp.onrender.com/static/logo.png",
            "contact_email": "youremail@example.com",
            "legal_info_url": "https://selenium-mcp.onrender.com/legal",
            "tools": tools
        }
        print(f"[INFO] /mcp/manifest served successfully ({len(tools)} tools)")
        return JSONResponse(content=manifest)

    except Exception as e:
        # Log and fail gracefully
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] /mcp/manifest exception: {e}\n{tb}")
        return JSONResponse(
            content={
                "error": "Manifest generation failed",
                "details": str(e),
                "trace": tb
            },
            status_code=500
        )


# ==========================================================
# Static Manifest Alias (/static/manifest.json)
# ==========================================================
@app.get("/static/manifest.json")
def serve_static_manifest():
    """
    Serve a stable manifest for external agents (Render-safe).
    Embeds tool definitions inline to avoid missing globals.
    """
    print(f"[INFO] Served /static/manifest.json → mirrors /mcp/schema ({MCP_VERSION})")

    # Inline tool list to ensure no async import issues
    tools = [
        {
            "name": "selenium_open_page",
            "description": "Open a URL in a headless Chrome browser and return the page title.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
        {
            "name": "selenium_click",
            "description": "Click an element by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
        {
            "name": "selenium_text",
            "description": "Get text content by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
        {
            "name": "selenium_screenshot",
            "description": "Save a PNG screenshot to /tmp and return its path.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"],
            },
        },
    ]

    schema = {
        "type": "mcp_server",
        "version": MCP_VERSION,
        "mcp_version": MCP_VERSION,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": MCP_VERSION,
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False,
        },
        "tools": tools,
    }

    return JSONResponse(
        content=schema,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Content-Disposition": 'inline; filename="manifest.json"',
        },
    )


# ==========================================================
# MCP Static Manifest (Safe path alias)
# ==========================================================
@app.get("/mcp/manifest")
def serve_mcp_manifest():
    """
    Serve version-pinned manifest for MCP discovery.
    Uses /mcp/manifest instead of /static/manifest.json
    to avoid FastAPI StaticFiles conflicts.
    """
    print(f"[INFO] Served /mcp/manifest → stable schema export ({MCP_VERSION})")

    tools = [
        {
            "name": "selenium_open_page",
            "description": "Open a URL in a headless Chrome browser and return the page title.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
        {
            "name": "selenium_click",
            "description": "Click an element by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
        {
            "name": "selenium_text",
            "description": "Get text content by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
        {
            "name": "selenium_screenshot",
            "description": "Save a PNG screenshot to /tmp and return its path.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"],
            },
        },
    ]

    schema = {
        "type": "mcp_server",
        "version": MCP_VERSION,
        "mcp_version": MCP_VERSION,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": MCP_VERSION,
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False,
        },
        "tools": tools,
    }

    return JSONResponse(
        content=schema,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Content-Disposition": 'inline; filename="manifest.json"',
        },
    )


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
@app.api_route("/live", methods=["GET", "POST"])
def live():
    return {"status": "live", "version": MCP_VERSION}


# ----------------------------------------------------------
# MCP Schema — Strictly Formatted Tool List for Agents
# ----------------------------------------------------------
@app.api_route("/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def serve_schema(request: Request):
    user_agent = request.headers.get("User-Agent", "unknown")
    print(f"[SCHEMA] Request from: {user_agent}")

    return JSONResponse({
        "version": MCP_VERSION,
        "tools": MCP_TOOLS_LIST
    })


# ==========================================================
# Canonical /mcp/schema → Primary Agent Builder manifest endpoint (self-healing, clean)
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_schema(request: Request):
    """Serve unified schema structure for OpenAI Agent Builder (self-healing)."""

    # ----------------------------------------------------------
    # Actively repair global MCP_VERSION if Render lost it
    # ----------------------------------------------------------
    global MCP_VERSION
    if not globals().get("MCP_VERSION") or globals().get("MCP_VERSION") in [None, "null", ""]:
        env_ver = os.getenv("MCP_VERSION")
        if env_ver and env_ver not in ["null", ""]:
            MCP_VERSION = env_ver
        else:
            MCP_VERSION = "v0.0.0-dev"
        print(f"[PATCH] MCP_VERSION repaired at runtime → {MCP_VERSION}")

    resolved_version = str(MCP_VERSION)

    # ----------------------------------------------------------
    # Build schema JSON
    # ----------------------------------------------------------
    schema = {
        "type": "mcp_server",
        "version": resolved_version,
        "mcp_version": resolved_version,
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": resolved_version,
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False
        },
        "tools": MCP_TOOLS_LIST
    }

    return JSONResponse(
        content=schema,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache"
        }
    )


# ----------------------------------------------------------
# Internal Debug Route — Reveals active MCP schema & tools
# ----------------------------------------------------------
@app.get("/mcp/internal_schema")
def internal_schema():
    try:
        return {
            "type": "mcp_server",
            "version": "v1",
            "server_name": "selenium-mcp",
            "description": "Internal diagnostic route exposing the active MCP tools list.",
            "manifest_schema": {
                "schema_type": "openai_manifest",
                "schema_version": "v1",
                "endpoint": f"{BASE_URL}/mcp/schema"
            },
            "tools_registered": len(MCP_TOOLS_LIST),
            "tool_names": [tool["name"] for tool in MCP_TOOLS_LIST],
            "tools": MCP_TOOLS_LIST
        }
    except Exception as e:
        return {
            "error": "Failed to load MCP internal schema.",
            "details": str(e)
        }


# ----------------------------------------------------------
# openapi.yaml route
# ----------------------------------------------------------
@app.get("/openapi.yaml")
def openapi_spec():
    return Response(yaml.dump({
        "openapi": "3.0.0",
        "info": {
            "title": "Selenium MCP API",
            "version": MCP_VERSION,
            "description": "OpenAPI spec for Selenium MCP tools"
        },
        "paths": { ... }  # define your 4 tools here
    }), media_type="application/x-yaml")


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

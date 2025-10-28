#!/usr/bin/env python3
# ==========================================================
# Selenium MCP — Headless Browser Automation (FastAPI MCP)
# Version: v20251027-FULL
# Author: Gene Arguelles, LLC
# ==========================================================
import os, datetime, platform, logging

# ----------------------------------------------------------
# ✅ Canonical MCP_VERSION bootstrap
# Ensures deterministic version tag across all workers
# ----------------------------------------------------------
if "MCP_VERSION" not in globals() or not globals().get("MCP_VERSION"):
    MCP_VERSION = os.getenv(
        "MCP_VERSION",
        f"v{datetime.date.today().strftime('%Y%m%d')}a"
    )
    print(f"[BOOT] MCP_VERSION pre-initialized as {MCP_VERSION}")

if not isinstance(MCP_VERSION, str) or not MCP_VERSION.startswith("v"):
    MCP_VERSION = f"v{datetime.date.today().strftime('%Y%m%d')}a"
    print(f"[BOOT] MCP_VERSION repaired to {MCP_VERSION}")

print(f"[INFO] Launching MCP Server (version={MCP_VERSION})")

import json     # ✅ Add this once here
import platform
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_tools import (
    selenium_open_page,
    selenium_click,
    selenium_get_text,
    selenium_screenshot,
)

# ----------------------------------------------------------
# Global version utility
# ----------------------------------------------------------
def get_mcp_version():
    return globals().get("MCP_VERSION", "v0.0.0-unknown")

# ==========================================================
# MCP Version Initialization (Safe Fallback)
# ==========================================================
import os, datetime

MCP_VERSION = os.getenv("MCP_VERSION", f"v{datetime.date.today().strftime('%Y%m%d')}a")

def get_mcp_version() -> str:
    """Return the canonical MCP version string (never None)."""
    return MCP_VERSION or "v0.0.0-unknown"

# ==========================================================
# === Banner ===
# ==========================================================
def startup_debug_banner():
    import datetime
    print(f"🚀 Render rebuild verified: {datetime.datetime.now().isoformat()} | MCP_VERSION: {get_mcp_version()}", flush=True)

startup_debug_banner()

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
# Global constants — must be defined before route declarations
# ==========================================================
SERVER_NAME = "Selenium MCP"
SERVER_DESC = "Headless browser automation tools for OpenAI Agent Builder."
CHROME_BINARY = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
BASE_URL = os.getenv("BASE_URL", "https://selenium-mcp.onrender.com")

# ==========================================================
# Force cache busting on Render build layer
# ==========================================================
FORCE_REBUILD_TAG = "v20251027b"  # ⬅️ bump this every time you need a new container
print(f"[BOOT] FORCE_REBUILD_TAG = {FORCE_REBUILD_TAG}")

# ==========================================================
# Failsafe: Ensure MCP_VERSION always initialized at import
# ==========================================================
# ----------------------------------------------------------
# Root manifest endpoint (for OpenAI Agent Builder)
# ----------------------------------------------------------
@app.get("/")
def root_manifest():
    return {
        "type": "manifest",
        "name": SERVER_NAME,
        "description": SERVER_DESC,
        "version": get_mcp_version()
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
        "version": get_mcp_version(),
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
    print(f"[INFO] Served /static/manifest.json → mirrors /mcp/schema ({get_mcp_version()})")

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
        "version": get_mcp_version(),
        "mcp_version": get_mcp_version(),
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": get_mcp_version(),
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
    print(f"[INFO] Served /mcp/manifest → stable schema export ({get_mcp_version()})")

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
        "version": get_mcp_version(),
        "mcp_version": get_mcp_version(),
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": get_mcp_version(),
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
        "mcp_version": get_mcp_version(),
        "version": get_mcp_version(),
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": get_mcp_version(),
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
        "mcp_version": get_mcp_version(),
        "version": get_mcp_version(),
        "server_info": {
            "name": SERVER_NAME,
            "description": SERVER_DESC,
           "version": get_mcp_version(),
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
    return {"status": "live", "version": get_mcp_version()}


# ----------------------------------------------------------
# MCP Schema — Strictly Formatted Tool List for Agents
# ----------------------------------------------------------
@app.api_route("/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_schema(request: Request):
    """Serve unified schema structure for OpenAI Agent Builder (literal-safe version)."""
    import os, platform, json, logging, sys, datetime
    from copy import deepcopy

    print(f"🧩 [CHECKPOINT] serve_schema() invoked fresh at {datetime.datetime.now().isoformat()}", flush=True)
    sys.stdout.flush()

    # ----------------------------------------------------------
    # Defensive: Clear old schema shadow if any
    # ----------------------------------------------------------
    if "schema" in globals():
        try:
            del globals()["schema"]
        except Exception:
            pass

    # ----------------------------------------------------------
    # Resolve version deterministically from canonical getter
    # ----------------------------------------------------------
    resolved_version = str(get_mcp_version() or "v0.0.0-dev")

    # ----------------------------------------------------------
    # Build canonical schema dictionary
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
            "multi_tool": False,
        },
        "tools": MCP_TOOLS_LIST,
    }

    # ----------------------------------------------------------
    # 🔒 Literal safety enforcement
    # ----------------------------------------------------------
    def literalize(obj):
        if isinstance(obj, dict):
            return {k: literalize(v) for k, v in obj.items()}
        elif obj is None:
            return "v0.0.0-dev"
        return str(obj)

    schema = literalize(schema)

    # 🩹 Ensure 'tools' is a proper JSON array (not stringified)
    import ast
    if isinstance(schema.get("tools"), str):
        try:
            schema["tools"] = ast.literal_eval(schema["tools"])
            print(f"🧠 [CHECKPOINT] Tools re-parsed into JSON array ({len(schema['tools'])} items)", flush=True)
        except Exception as e:
            print(f"⚠️ [WARN] Tools list could not be parsed: {e}", flush=True)

    # ----------------------------------------------------------
    # 🩹 Post-literalization repair for tool list
    # ----------------------------------------------------------
    if isinstance(schema.get("tools"), str):
        import ast
        try:
            parsed_tools = ast.literal_eval(schema["tools"])
            if isinstance(parsed_tools, list):
                schema["tools"] = parsed_tools
                print(f"🧠 [CHECKPOINT] Tools list successfully re-parsed: {len(parsed_tools)} tools", flush=True)
            else:
                print("⚠️ [WARN] Tools re-parsed but not list type — replaced with []", flush=True)
                schema["tools"] = []
        except Exception as e:
            print(f"❌ [ERROR] Failed to re-parse tools list: {e}", flush=True)
            schema["tools"] = []    

    # ----------------------------------------------------------
    # 🩹 Post-literalization repair for null fields
    # ----------------------------------------------------------
    resolved_version = get_mcp_version()
    if not schema.get("mcp_version"):
        schema["mcp_version"] = resolved_version
    if "server_info" in schema:
        if not schema["server_info"].get("version"):
            schema["server_info"]["version"] = resolved_version

    # Guaranteed visible checkpoint
    print(f"🩺 [CHECKPOINT] Schema repaired → version={schema.get('version')} | mcp_version={schema.get('mcp_version')} | server_info.version={schema.get('server_info', {}).get('version')}", flush=True)

    # ----------------------------------------------------------
    # ✅ Safe serialization (deepcopy + JSON load)
    # ----------------------------------------------------------
    payload = deepcopy(schema)
    safe_json = json.loads(json.dumps(payload, default=str))

    # 🩹 Final pre-return repair (after deepcopy & serialization)
    resolved_version = get_mcp_version()
    for key in ("version", "mcp_version"):
        safe_json[key] = resolved_version
    if isinstance(safe_json.get("server_info"), dict):
        safe_json["server_info"]["version"] = resolved_version

    # ----------------------------------------------------------
    # 🚀 Guaranteed visible checkpoint
    # ----------------------------------------------------------
    print(
        "🚀 [CHECKPOINT] serve_schema() finalized successfully!\n"
        f"Resolved version: {resolved_version}\n"
        f"Schema summary:\n{json.dumps({k: safe_json.get(k) for k in ['version', 'mcp_version', 'server_info']}, indent=2)}",
        flush=True
    )

    # ----------------------------------------------------------
    # 🧩 Force literal-safe JSON encoding to preserve all values
    # ----------------------------------------------------------
    # 🩹 Ensure tools remain as real JSON arrays (not stringified)
    if isinstance(schema.get("tools"), str):
        try:
            import ast
            schema["tools"] = ast.literal_eval(schema["tools"])
        except Exception as e:
            print(f"[WARN] Could not re-parse tools list: {e}", flush=True) 
 
    final_json_str = json.dumps(safe_json, ensure_ascii=False, indent=2)
    final_payload = json.loads(final_json_str)

    print(
        "✅ [FINAL-PASS] Returning fully literalized schema →",
        json.dumps(
            {
                "version": final_payload.get("version"),
                "mcp_version": final_payload.get("mcp_version"),
                "server_info.version": final_payload.get("server_info", {}).get("version"),
            },
            indent=2,
        ),
        flush=True,
    )

    # ----------------------------------------------------------
    # ✅ Final literal lock: bypass FastAPI encoder
    # ----------------------------------------------------------
    import json
    final_json_str = json.dumps(
        safe_json,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    # 🚀 Visible checkpoint (always prints in Render logs)
    print(
        f"🚀 [FINAL-RETURN] MCP schema literalized:\n"
        f"version={resolved_version}\n"
        f"{final_json_str[:600]}...\n",  # truncates long output for readability
        flush=True
    )

    from fastapi.responses import Response
    return Response(
        content=final_json_str,
        media_type="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )

# ----------------------------------------------------------
# MCP Status — Lightweight Health & Compliance Check
# ----------------------------------------------------------
@app.get("/mcp/status")
def mcp_status():
    """Return simple MCP readiness & compliance status for remote checks."""
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "status": "ok",
        "message": "Selenium MCP server is live and compliant.",
        "mcp_version": get_mcp_version(),
        "tools_registered": len(MCP_TOOLS_LIST),
    })

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
            "version": get_mcp_version(),
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
# 🧠 MCP Invocation Endpoint — active dispatcher (MCP-compliant)
# ----------------------------------------------------------
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    """
    Handles invocation requests from Agent Builder and executes Selenium tools.
    Compatible with both OpenAI Agent Builder and MCP validation.
    """
    data = await request.json()
    tool = data.get("tool")
    args = data.get("arguments") or data.get("args") or data.get("params") or {}

    if not tool:
        return JSONResponse({"error": "Missing 'tool' argument."}, status_code=400)

    if tool == "selenium_open_page":
        url = args.get("url")
        if not url:
            return JSONResponse({"error": "Missing 'url' argument."}, status_code=400)
        result = selenium_open_page(url)
        return JSONResponse({"status": "success", "tool": tool, "result": result})

    elif tool == "selenium_click":
        selector = args.get("selector")
        if not selector:
            return JSONResponse({"error": "Missing 'selector' argument."}, status_code=400)
        result = selenium_click(selector)
        return JSONResponse({"status": "success", "tool": tool, "result": result})

    elif tool == "selenium_get_text":
        selector = args.get("selector")
        if not selector:
            return JSONResponse({"error": "Missing 'selector' argument."}, status_code=400)
        result = selenium_get_text(selector)
        return JSONResponse({"status": "success", "tool": tool, "result": result})

    elif tool == "selenium_screenshot":
        filename = args.get("filename", "screenshot.png")
        result = selenium_screenshot(filename)
        return JSONResponse({"status": "success", "tool": tool, "result": result})

    else:
        return JSONResponse(
            {"error": f"Unknown tool '{tool}'."}, status_code=404
        )

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
    print(f"[INFO] Launching MCP Server on port 10000 (version={resolved_version})")
    uvicorn.run(app, host="0.0.0.0", port=10000)

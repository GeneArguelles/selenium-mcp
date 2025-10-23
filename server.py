#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server (auto-versioned)
# ==========================================================
# Provides headless browser automation endpoints for OpenAI
# Agent Builder via the Model Context Protocol (MCP).
# ==========================================================

import os
import re
import time
import json
import platform
import hashlib
import subprocess
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================================================
# Environment & Globals
# ==========================================================
RENDER_CHROME_PATH = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CHROME_BINARY = (
    RENDER_CHROME_PATH if os.path.exists(RENDER_CHROME_PATH) else LOCAL_CHROME_PATH
)

SERVER_NAME = "Selenium MCP"
SERVER_DESC = "Headless browser automation tools for OpenAI Agent Builder."
APP_START_TIME = time.time()

# ==========================================================
# MCP Tool Definitions
# ==========================================================
MCP_TOOLS_LIST = [
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

# ==========================================================
# Versioning
# ==========================================================
VERSION_FILE = "mcp_version.txt"

def get_next_version():
    today = datetime.utcnow().strftime("%Y%m%d")
    base = f"v{today}"

    if not os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "w") as f:
            f.write(base + "a")
        return base + "a"

    with open(VERSION_FILE, "r") as f:
        last = f.read().strip()

    match = re.match(rf"v{today}([a-z])", last)
    if match:
        new_suffix = chr(ord(match.group(1)) + 1)
        new_version = f"{base}{new_suffix}"
    else:
        new_version = base + "a"

    with open(VERSION_FILE, "w") as f:
        f.write(new_version)

    return new_version

MCP_VERSION = get_next_version()
print(f"[INFO] Auto-incremented MCP version: {MCP_VERSION}")

# ==========================================================
# FastAPI Init
# ==========================================================
app = FastAPI(title=f"{SERVER_NAME} Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://chat.openai.com", "https://builder.openai.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

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
            "live": f"{request.base_url}live",
        },
    }

# ==========================================================
# Canonical /mcp/schema
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_schema(request: Request):
    print(f"[INFO] Served /mcp/schema (MCP_VERSION={MCP_VERSION})")
    return JSONResponse(
        content={
            "type": "mcp_server",
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
            "tools": MCP_TOOLS_LIST,
        },
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )

# ==========================================================
# Versioned /v*/mcp/schema alias
# ==========================================================
@app.api_route(f"/{MCP_VERSION}/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_versioned_schema(request: Request):
    print(f"[INFO] Served versioned /{MCP_VERSION}/mcp/schema → canonical /mcp/schema")
    return serve_schema(request)

# ==========================================================
# Canonical /live Schema
# ==========================================================
last_success_mode = "strict"
last_switch_time = None

@app.api_route("/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_live(request: Request):
    global last_success_mode, last_switch_time
    client_ua = request.headers.get("User-Agent", "unknown")

    print(f"\n[INFO] /live hit by {client_ua}")
    print(f"[INFO] Mode={last_success_mode} | MCP_VERSION={MCP_VERSION}")

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
        "tools": MCP_TOOLS_LIST,
    }

    last_success_mode = "strict"
    last_switch_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    return JSONResponse(content=schema)

# ==========================================================
# Versioned /v*/live alias
# ==========================================================
@app.api_route("/{version}/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_versioned_live(request: Request, version: str):
    print(f"[INFO] Served /{version}/live → canonical /live")
    return serve_live(request)

# ==========================================================
# /mcp/invoke — Tool execution
# ==========================================================
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict | None = None

@app.api_route("/mcp/invoke", methods=["POST", "GET"])
def invoke_tool(req: InvokeRequest | None = None):
    if req is None:
        return {"status": "ready", "message": "MCP invoke endpoint alive."}

    print(f"[INFO] Invoked tool: {req.tool}")
    if req.tool == "selenium_open_page":
        url = req.arguments.get("url") if req.arguments else None
        if not url:
            return JSONResponse(content={"error": "Missing 'url' argument."}, status_code=400)

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
            return {"error": str(e)}

    return {"error": f"Unknown tool: {req.tool}"}

# ==========================================================
# /health
# ==========================================================
@app.get("/health")
def health_check():
    uptime = round(time.time() - APP_START_TIME, 2)
    return {
        "status": "healthy" if os.path.exists(CHROME_BINARY) else "unhealthy",
        "uptime_seconds": uptime,
        "chrome_path": CHROME_BINARY,
        "MCP_VERSION": MCP_VERSION,
    }

# ==========================================================
# Local Run Entry
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Launching MCP Server on port 10000 (version={MCP_VERSION})")
    uvicorn.run(app, host="0.0.0.0", port=10000)

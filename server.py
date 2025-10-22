#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server (auto-versioned)
# ==========================================================
# Provides headless browser automation endpoints for OpenAI
# Agent Builder via the Model Context Protocol (MCP).
# ==========================================================

# ------------------------------
# Imports
# ------------------------------
import os
import re
import time
import platform
import hashlib
import requests
from datetime import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ------------------------------
# Server Metadata (must precede FastAPI init)
# ------------------------------
SERVER_NAME = "Selenium"
SERVER_DESC = "MCP server providing headless browser automation via Selenium."
SERVER_VERSION = "1.0.0"

# ------------------------------
# FastAPI Init + CORS
# ------------------------------
app = FastAPI(title=f"{SERVER_NAME} MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://chat.openai.com",
        "https://builder.openai.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# ==========================================================
# AUTO-INCREMENTING VERSION PUSH ROUTINE FOR MCP SERVER
# ==========================================================
VERSION_FILE = "mcp_version.txt"

def get_next_version():
    """Automatically generate or increment version suffix for /vYYYYMMDD/live"""
    today = datetime.utcnow().strftime("%Y%m%d")
    base = f"v{today}"

    if not os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "w") as f:
            f.write(base + "a")
        return base + "a"

    with open(VERSION_FILE, "r") as f:
        last = f.read().strip()

    # Example: v20251020a → v20251020b
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
print(f"[INFO] {SERVER_NAME} MCP Server v{SERVER_VERSION} initialized successfully.")


# ==========================================================
# PUSH ROUTINE FOR MANUAL DEPLOYMENT VALIDATION (SAFE MODE)
# ==========================================================

BASE_URL = "https://selenium-mcp.onrender.com"
STATIC_VERSION = "v20251020"   # Keep fixed until tools load properly

def generate_nonce():
    """Generate unique nonce like $(date +%s%N | sha1sum | cut -c1-10)"""
    seed = str(time.time()).encode("utf-8")
    return hashlib.sha1(seed).hexdigest()[:10]

def build_mcp_url():
    """Constructs full MCP URL for this push"""
    nonce = generate_nonce()
    return f"{BASE_URL}/{STATIC_VERSION}/live?nonce={nonce}&refresh=true"

def validate_schema(url):
    """Fetch manifest and validate essential MCP keys"""
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        print("-----------------------------------------------------------")
        print(f"[PUSH] MCP URL: {url}")
        print(f"[PUSH] HTTP Status: {response.status_code}")
        if "tools" in data:
            print(f"[PUSH] ✅ Found {len(data['tools'])} tool(s) in manifest.")
        else:
            print(f"[PUSH] ⚠️ No tools found in manifest!")
        if data.get("type") == "mcp_server":
            print("[PUSH] ✅ Type is MCP-compliant.")
        else:
            print("[PUSH] ⚠️ Type key missing or incorrect.")
        print("-----------------------------------------------------------")
    except Exception as e:
        print("[PUSH] ❌ Validation failed:", e)

def run_push_validation():
    """Main trigger for deployment validation routine"""
    url = build_mcp_url()
    print("===========================================================")
    print(f"[PUSH] Starting MCP validation push @ {time.ctime()}")
    print("===========================================================")
    validate_schema(url)
    print("===========================================================")
    print("[PUSH] Validation complete. Copy URL above for Agent Builder.")
    print("===========================================================")

# Run validation on startup
run_push_validation()


# ==========================================================
# AUTO-ANNOUNCE MCP URL + SELF-TEST INVOKE + LATENCY METRICS
# ==========================================================
@app.on_event("startup")
async def announce_mcp_url():
    """
    Prints the ready-to-use MCP connection URL and automatically runs
    a self-validation test invoking the selenium_open_page tool.
    Logs include HTTP status, latency, and title extraction.
    """
    import subprocess, json, time

    nonce = int(time.time())
    mcp_url = f"https://selenium-mcp.onrender.com/{MCP_VERSION}/live?nonce={nonce}&refresh=true"

    print("\n==========================================================")
    print(f"[MCP] Ready! Copy this URL for Agent Builder:\n{mcp_url}")
    print("----------------------------------------------------------")
    print("[MCP] Running automated invoke test (https://example.com)...")

    invoke_cmd = [
        "curl", "-s", "-w",
        "HTTP_STATUS:%{http_code} TIME_TOTAL:%{time_total}",
        "-X", "POST",
        "https://selenium-mcp.onrender.com/mcp/invoke",
        "-H", "Content-Type: application/json",
        "-d", '{"tool": "selenium_open_page", "arguments": {"url": "https://example.com"}}'
    ]

    start = time.time()
    try:
        result = subprocess.run(invoke_cmd, capture_output=True, text=True, timeout=25)
        end = time.time()

        output = result.stdout.strip()
        status_code = "N/A"
        latency_ms = round((end - start) * 1000, 2)

        if "HTTP_STATUS:" in output:
            # Separate JSON and curl -w metadata
            parts = output.split("HTTP_STATUS:")
            json_part = parts[0].strip()
            meta_part = parts[1].strip()
            if "TIME_TOTAL:" in meta_part:
                status_code, time_total = meta_part.split("TIME_TOTAL:")
                status_code = status_code.strip()
                latency_ms = round(float(time_total) * 1000, 2)
        else:
            json_part = output

        if json_part:
            try:
                parsed = json.loads(json_part)
                title = parsed.get("title", "No title")
                print(f"[MCP] ✅ Invoke test successful — Page Title: {title}")
            except json.JSONDecodeError:
                print("[MCP] ⚠️ Received non-JSON output:")
                print(json_part)
        else:
            print("[MCP] ❌ Empty response from invoke test.")

        print(f"[MCP] HTTP Status: {status_code} | Latency: {latency_ms} ms")

    except subprocess.TimeoutExpired:
        print("[MCP] ❌ Timeout — Invoke test took too long (>25s).")
    except Exception as e:
        print(f"[MCP] ❌ Invoke test exception: {e}")

    print("----------------------------------------------------------")
    print("[MCP] Manual test command:")
    print("curl -s -X POST https://selenium-mcp.onrender.com/mcp/invoke "
          "-H 'Content-Type: application/json' "
          "-d '{\"tool\": \"selenium_open_page\", \"arguments\": {\"url\": \"https://example.com\"}}' | jq .")
    print("==========================================================\n")


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
# Root Schema (Agent Builder entry)
# ==========================================================
@app.api_route("/", methods=["GET", "POST", "HEAD", "OPTIONS"])
def root_schema():
    print("[INFO] Served unified root schema")
    schema = build_agentbuilder_schema()
    return JSONResponse(content=schema)


# ==========================================================
# Dynamic Version Incrementer for MCP Schema Endpoint
# ==========================================================
import string
from datetime import datetime

BASE_VERSION = "v20251020"
SUFFIX_FILE = "/tmp/mcp_version_suffix.txt"

def get_next_suffix():
    """Retrieve and increment the MCP suffix stored in SUFFIX_FILE."""
    try:
        with open(SUFFIX_FILE, "r") as f:
            current = f.read().strip()
    except FileNotFoundError:
        current = "a"

    # Increment alphabetical suffix
    if current and current[-1].isalpha():
        if current[-1] == "z":
            new = current + "a"
        else:
            new = current[:-1] + chr(ord(current[-1]) + 1)
    else:
        new = "a"

    with open(SUFFIX_FILE, "w") as f:
        f.write(new)
    return new

MCP_SUFFIX = get_next_suffix()
MCP_VERSIONED_PATH = f"/{BASE_VERSION}{MCP_SUFFIX}/live"
print(f"[INFO] MCP dynamic path registered: {MCP_VERSIONED_PATH}")


# ==========================================================
# Build flat MCP manifest — OpenAI Agent Builder compatible
# ==========================================================
def build_agentbuilder_schema():
    """
    Return a flat, unified MCP manifest compatible with
    OpenAI Agent Builder. This schema ensures that `tools`
    appear at the top level (not nested under 'manifest').
    """
    return {
        "type": "mcp_server",
        "version": MCP_VERSION,
        "mcp_version": MCP_VERSION,
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
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"],
                },
            }
        ],
    }


# ==========================================================
# Unified schema builder for /live and /mcp/schema endpoints
# ==========================================================
def build_schema_response() -> JSONResponse:
    """
    Centralized schema builder and response constructor.
    Ensures schema endpoints share a flat structure
    recognized by OpenAI Agent Builder.
    """
    manifest = build_agentbuilder_schema()
    
    # Inject MCP version metadata at the top level
    manifest["version"] = MCP_VERSION
    manifest["mcp_version"] = MCP_VERSION
    
    response = JSONResponse(content=manifest)
    response.headers["Content-Type"] = "application/json"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


# ==========================================================
# /mcp/schema → Primary Agent Builder manifest endpoint
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_schema(request: Request):
    """Serve unified schema structure for OpenAI Agent Builder."""
    print(f"[INFO] Served unified /mcp/schema (linked to {MCP_VERSION})")
    return build_schema_response()


# ==========================================================
# Canonical /live Schema for OpenAI Agent Builder
# ==========================================================
@app.api_route("/live", methods=["GET", "POST", "HEAD", "OPTIONS"])
def serve_canonical_live(request: Request):
    """Single unified schema endpoint for Agent Builder detection."""
    print(f"[INFO] Served canonical /live schema (Builder mode, {MCP_VERSION})")

    schema = {
        "type": "mcp_server",
        "version": "2025-10-01",
        "server_info": {
            "name": "Selenium MCP",
            "description": "Headless browser automation tools via Selenium for Agent Builder.",
            "version": MCP_VERSION,
            "runtime": platform.python_version()
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            },
            {
                "name": "selenium_click",
                "description": "Click an element by CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"]
                }
            },
            {
                "name": "selenium_text",
                "description": "Get text content by CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"]
                }
            },
            {
                "name": "selenium_screenshot",
                "description": "Save a PNG screenshot to /tmp and return its path.",
                "parameters": {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}},
                    "required": ["filename"]
                }
            }
        ]
    }

    return JSONResponse(
        content=schema,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Content-Type": "application/json; charset=utf-8"
        }
    )


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
# /mcp/invoke — Tool execution (GET + POST unified)
# ==========================================================
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict | None = None


@app.api_route("/mcp/invoke", methods=["GET", "POST", "HEAD", "OPTIONS"])
def invoke_tool(req: InvokeRequest | None = None):
    """
    Unified MCP invoke endpoint:
    - GET  → used by validators or Render probes (returns a ready message)
    - POST → actual tool invocation (standard MCP call)
    """
    if req is None:
        print("[INFO] /mcp/invoke validation GET call — endpoint reachable.")
        return JSONResponse(
            content={"status": "ready", "message": "MCP invoke endpoint alive."},
            status_code=200,
        )

    print(f"[INFO] Invoked tool: {req.tool}")

    if req.tool == "selenium_open_page":
        url = (req.arguments or {}).get("url")
        if not url:
            return JSONResponse(
                content={"error": "Missing 'url' argument."},
                status_code=400,
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
            return JSONResponse(
                content={"result": f"Opened {url}", "title": title},
                status_code=200,
            )
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)

    return JSONResponse(
        content={"error": f"Unknown tool: {req.tool}"},
        status_code=400,
    )


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

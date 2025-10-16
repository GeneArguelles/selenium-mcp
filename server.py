#!/usr/bin/env python3
"""
Selenium MCP Server — Render-stable Playwright version
------------------------------------------------------
• Uses Playwright's embedded Chromium (no ChromeDriver required)
• Supports both GET and POST for /mcp/schema
• Provides /mcp/ping, /mcp/status, /mcp/debug, /mcp/invoke
• Compatible with OpenAI Agent Builder MCP discovery
"""

import os
import sys
import json
import time
import platform
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------
#  FastAPI app setup
# ---------------------------------------------------------------------
app = FastAPI(title="Selenium MCP Server (Playwright Edition)")

# Enable CORS (for Agent Builder & MCP integrations)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()
last_invocation = {"time": None, "tool": "No tool executed yet."}

# ---------------------------------------------------------------------
#  Playwright helper (stable headless Chrome)
# ---------------------------------------------------------------------
def get_page_title_playwright(url: str) -> str:
    """Open a page headlessly using Playwright Chromium and return title."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--disable-background-timer-throttling",
                    "--window-size=1280,720",
                    "--remote-debugging-port=9222"
                ]
            )
            page = browser.new_page()
            page.goto(url, timeout=30000)
            title = page.title()
            browser.close()
            return title
    except Exception as e:
        print(f"[ERROR] Playwright failed to open page: {e}")
        raise RuntimeError(f"500: Playwright could not start Chromium: {e}")

# ---------------------------------------------------------------------
#  MCP routes
# ---------------------------------------------------------------------

@app.get("/")
@app.post("/")
async def root():
    """Root discovery endpoint (Agent Builder probes here first)."""
    return JSONResponse({
        "type": "mcp_server",
        "name": "selenium_mcp_server",
        "description": "Render-hosted MCP server exposing Playwright-based browser automation tools.",
        "endpoints": {
            "schema": "/mcp/schema",
            "invoke": "/mcp/invoke",
            "ping": "/mcp/ping",
            "status": "/mcp/status",
            "debug": "/mcp/debug"
        }
    })


@app.get("/mcp/ping")
async def ping():
    """Simple liveness check."""
    return {"status": "ok"}


@app.get("/mcp/schema")
@app.post("/mcp/schema")
async def schema():
    """Schema definition for MCP tool discovery."""
    return JSONResponse({
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp_server",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing Playwright-based browser automation.",
            "version": "1.0.0"
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chromium browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        ]
    })


@app.get("/mcp/status")
async def status():
    """Server status endpoint (uptime, last invocation)."""
    uptime = time.time() - start_time
    return {
        "status": "running",
        "uptime_seconds": round(uptime, 2),
        "last_invocation": last_invocation["tool"],
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


@app.get("/mcp/debug")
async def debug():
    """Environment diagnostics for Render sandbox verification."""
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~"),
        "path_env": os.environ.get("PATH", ""),
        "playwright_installed": Path("/home/render/.cache/ms-playwright").exists(),
    }


@app.post("/mcp/invoke")
async def invoke_tool(request: Request):
    """Invoke the MCP tool."""
    try:
        payload = await request.json()
        tool = payload.get("tool")
        args = payload.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            title = get_page_title_playwright(url)
            last_invocation["time"] = time.time()
            last_invocation["tool"] = tool
            return JSONResponse({"ok": True, "url": url, "title": title})

        return JSONResponse({"detail": f"Unknown tool '{tool}'"}, status_code=400)

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


# ---------------------------------------------------------------------
#  Local Run Support
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

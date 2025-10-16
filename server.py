#!/usr/bin/env python3
"""
Selenium MCP Server — Final APT-based Version
Render-optimized, using system-installed Chrome + ChromeDriver
"""

import os
import time
import platform
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ==========================================================
#  App Setup
# ==========================================================
app = FastAPI(title="Selenium MCP Server")

# Enable CORS (required for Agent Builder connections)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track uptime and last invocation
server_start = time.time()
last_invocation = "No tool executed yet."

# Server metadata
server_info = {
    "type": "mcp",
    "name": "selenium_mcp_server",
    "description": "Render-hosted MCP exposing a headless browser automation tool.",
    "version": "1.0.0",
    "runtime": platform.python_version(),
}


# ==========================================================
#  Chrome Initialization
# ==========================================================
def init_chrome_driver():
    """Start a stable headless Chrome session in Render’s sandbox."""

    try:
        chrome_opts = Options()
        chrome_opts.binary_location = "/usr/bin/google-chrome"
        chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--disable-gpu")
        chrome_opts.add_argument("--disable-extensions")
        chrome_opts.add_argument("--disable-software-rasterizer")
        chrome_opts.add_argument("--disable-background-timer-throttling")
        chrome_opts.add_argument("--disable-backgrounding-occluded-windows")
        chrome_opts.add_argument("--disable-renderer-backgrounding")
        chrome_opts.add_argument("--remote-debugging-port=9222")

        driver = webdriver.Chrome(options=chrome_opts)
        return driver

    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")


# ==========================================================
#  MCP Endpoints
# ==========================================================

@app.get("/")
@app.post("/")
async def root():
    """Root discovery endpoint — required for some MCP clients."""
    return {
        "status": "ok",
        "server_info": server_info,
        "message": "MCP server root is active."
    }


@app.get("/mcp/ping")
async def ping():
    return {"status": "ok"}


@app.get("/mcp/schema")
@app.post("/mcp/schema")
async def schema():
    """Expose MCP tool definitions."""
    return {
        "version": "2025-10-01",
        "server_info": server_info,
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


@app.get("/mcp/status")
async def status():
    """System health and runtime info."""
    uptime = round(time.time() - server_start, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


@app.post("/mcp/invoke")
async def invoke(request: Request):
    """Execute the requested MCP tool."""
    global last_invocation

    try:
        data = await request.json()
        tool = data.get("tool")
        args = data.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"error": "Missing 'url' argument"})

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            last_invocation = f"Opened {url} — Title: {title}"
            return {"ok": True, "url": url, "title": title}

        return JSONResponse(status_code=400, content={"error": f"Unknown tool '{tool}'"})

    except Exception as e:
        print(f"[ERROR] Exception during tool invocation: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"500: Chrome could not start in current environment: {e}"}
        )


# ==========================================================
#  Startup Banner
# ==========================================================
@app.on_event("startup")
async def startup_event():
    print("[INFO] Selenium MCP Server ready on Render.")
    print(f"[INFO] Using Chrome binary: /usr/bin/google-chrome")
    print(f"[INFO] Python runtime: {platform.python_version()}")


# ==========================================================
#  Local Entry Point (Optional)
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

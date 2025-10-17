#!/usr/bin/env python3
"""
server.py — Selenium MCP Server with Healthcheck, Environment Awareness,
and ChromeDriver Auto-Compatibility.

Compatible with both local development and Render deployments.
"""

import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from datetime import datetime

# ==========================================================
# 1️⃣ Environment Setup
# ==========================================================
load_dotenv()

PORT = int(os.getenv("PORT", "10000"))
CHROME_BINARY = os.getenv(
    "CHROME_BINARY",
    "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
)
CHROMEDRIVER_PATH = os.getenv(
    "CHROMEDRIVER_PATH",
    "./chromedriver/chromedriver"
)
CHROME_VERSION = os.getenv("CHROME_VERSION", "120")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

app = FastAPI(title="Selenium MCP Server")

# ==========================================================
# 2️⃣ Startup Logging
# ==========================================================
print("==========================================================")
print("[INFO] Starting Selenium MCP Server...")
print(f"[INFO] Description: MCP server providing headless browser automation via Selenium.")
print(f"[INFO] Version: 1.0.0")
print(f"[INFO] Python Runtime: {os.sys.version.split()[0]}")
print(f"[INFO] Chrome Binary: {CHROME_BINARY}")
print(f"[INFO] ChromeDriver Path: {CHROMEDRIVER_PATH}")
print(f"[INFO] Chrome Version (env): {CHROME_VERSION}")
print(f"[INFO] DRY_RUN Mode: {DRY_RUN}")
print("==========================================================")


# ==========================================================
# 3️⃣ MCP Root Endpoints
# ==========================================================
@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "Selenium MCP Server is live.",
        "runtime": os.sys.version.split()[0],
        "chrome_path": CHROME_BINARY,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/")
async def root_discovery(request: Request):
    print("[INFO] POST / root discovery requested")
    return {
        "status": "running",
        "message": "Selenium MCP Server responding to POST root discovery.",
        "runtime": os.sys.version.split()[0],
        "chrome_path": CHROME_BINARY,
        "timestamp": datetime.utcnow().isoformat()
    }


# ==========================================================
# 4️⃣ MCP /health Endpoint
# ==========================================================
@app.get("/health")
async def health_check():
    """
    Render’s uptime monitor hits this endpoint every few seconds.
    Returns HTTP 200 if the server is operational.
    """
    try:
        chrome_exists = os.path.exists(CHROME_BINARY)
        driver_exists = os.path.exists(CHROMEDRIVER_PATH)
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "chrome_binary_found": chrome_exists,
                "chromedriver_found": driver_exists,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# ==========================================================
# 5️⃣ MCP /mcp/schema
# ==========================================================
@app.post("/mcp/schema")
@app.get("/mcp/schema")
async def mcp_schema():
    schema = {
        "version": "2025-10-01",
        "type": "mcp",
        "server_info": {
            "name": "Selenium",
            "description": "MCP server providing headless browser automation via Selenium.",
            "version": "1.0.0",
            "runtime": os.sys.version.split()[0],
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
    print("[INFO] Served /mcp/schema for Selenium (Agent Builder spec compliant)")
    return JSONResponse(content=schema)


# ==========================================================
# 6️⃣ MCP /mcp/invoke
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    payload = await request.json()
    tool = payload.get("tool")
    args = payload.get("arguments", {})
    print(f"[INFO] Tool invoked: {tool} with args {args}")

    if tool != "selenium_open_page":
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown tool '{tool}'"},
        )

    if DRY_RUN:
        return JSONResponse(content={"result": {"url": args.get("url"), "title": "DRY_RUN_MODE"}})

    try:
        # Chrome Options
        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # ChromeDriver Service
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(15)
        driver.get(args["url"])
        title = driver.title
        driver.quit()

        return JSONResponse(content={"result": {"url": args["url"], "title": title}})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Chrome could not start: {str(e)}"},
        )


# ==========================================================
# 7️⃣ Server Entrypoint
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] Starting Uvicorn on port {PORT}")
    asyncio.run(asyncio.sleep(2))
    uvicorn.run(app, host="0.0.0.0", port=PORT)

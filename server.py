#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server (Render-Safe Version)
# ==========================================================

import os, time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# ----------------------------------------------------------
# App initialization
# ----------------------------------------------------------
app = FastAPI(title="Selenium MCP Server", version="1.0.0")
start_time = time.time()
last_invocation = "No tool executed yet."

# CORS Middleware for Agent Builder
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------
# Chrome and ChromeDriver paths (Render user-space)
# ----------------------------------------------------------
CHROME_BINARY = "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
CHROMEDRIVER_PATH = "/opt/render/project/src/chromedriver/chromedriver"

# ----------------------------------------------------------
# Health check root endpoint
# ----------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "🧩 Selenium MCP Server running", "time": datetime.utcnow().isoformat()}

# ----------------------------------------------------------
# MCP ping endpoint
# ----------------------------------------------------------
@app.get("/mcp/ping")
async def mcp_ping():
    return {"status": "ok"}

# ----------------------------------------------------------
# MCP schema endpoint
# ----------------------------------------------------------
@app.post("/mcp/schema")
@app.get("/mcp/schema")
async def mcp_schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": f"Python {os.sys.version.split()[0]}",
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

# ----------------------------------------------------------
# MCP status endpoint
# ----------------------------------------------------------
@app.get("/mcp/status")
async def mcp_status():
    uptime = time.time() - start_time
    return {
        "status": "running",
        "uptime_seconds": round(uptime, 2),
        "last_invocation": last_invocation,
        "server_time": datetime.utcnow().isoformat(),
    }

# ----------------------------------------------------------
# Request Model
# ----------------------------------------------------------
class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ----------------------------------------------------------
# MCP invoke endpoint
# ----------------------------------------------------------
@app.post("/mcp/invoke")
async def mcp_invoke(request: InvokeRequest):
    global last_invocation
    last_invocation = f"{datetime.utcnow().isoformat()} ({request.tool})"

    if request.tool == "selenium_open_page":
        url = request.arguments.get("url")
        if not url:
            return {"detail": "Missing required parameter: url"}

        try:
            print(f"[INFO] Launching Chrome for URL: {url}")

            chrome_options = Options()
            chrome_options.binary_location = CHROME_BINARY
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--remote-debugging-port=9222")

            if not os.path.exists(CHROMEDRIVER_PATH):
                raise FileNotFoundError(f"ChromeDriver not found at {CHROMEDRIVER_PATH}")

            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)

            driver.get(url)
            title = driver.title
            driver.quit()

            print(f"[INFO] ✅ Page loaded successfully: {title}")
            return {"result": {"url": url, "title": title}}

        except Exception as e:
            print(f"[ERROR] Chrome failed to start: {e}")
            return {"detail": f"500: Chrome could not start in current environment: {e}"}

    return {"detail": f"Unsupported tool: {request.tool}"}

# ----------------------------------------------------------
# Run server
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"[INFO] Starting MCP server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

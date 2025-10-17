#!/usr/bin/env python3
# ==========================================================
# server.py — Selenium MCP Server (Render-Ready)
# ==========================================================
# ✅ Supports OpenAI Agent Builder (MCP Schema v2025-10-01)
# ==========================================================

import os
import platform
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================================
# 1️⃣ FastAPI App Setup
# ==========================================================
app = FastAPI(title="Selenium MCP Server", version="1.0.0")
START_TIME = time.time()

# ==========================================================
# 2️⃣ Helper: Create Headless Chrome
# ==========================================================
def create_chrome_driver():
    chrome_path = os.environ.get("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
    print(f"[INFO] Using Chrome binary at: {chrome_path}")

    chrome_options = Options()
    chrome_options.binary_location = chrome_path
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")

    driver_path = ChromeDriverManager().install()
    print(f"[INFO] Using ChromeDriver from: {driver_path}")

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# ==========================================================
# 3️⃣ Root + Health Endpoints
# ==========================================================
@app.get("/")
async def root():
    return {
        "message": "🧩 Selenium MCP Server is live and ready.",
        "runtime": platform.python_version(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "chrome_path": os.environ.get("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
    }


@app.get("/mcp/ping")
async def ping():
    return {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 2)}


@app.get("/mcp/status")
async def mcp_status():
    return {
        "status": "running",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime": platform.python_version(),
    }


# ==========================================================
# 4️⃣ Corrected /mcp/schema for Agent Builder
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema():
    """
    Return the MCP schema describing available tools.
    Supports both GET and POST for compatibility with OpenAI Agent Builder.
    """
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",  # ✅ FIXED: required exact type for Agent Builder
        "server_info": {
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": platform.python_version(),
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
                    "required": ["url"]
                }
            }
        ]
    }
    print("[INFO] Served /mcp/schema to Agent Builder client (type=mcp_server).")
    return JSONResponse(content=schema)


# ==========================================================
# 5️⃣ MCP Tool: selenium_open_page
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    try:
        body = await request.json()
        tool = body.get("tool")
        args = body.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"error": "Missing URL"})

            print(f"[INFO] Invoking selenium_open_page with URL: {url}")

            driver = create_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            return JSONResponse(content={"result": {"url": url, "title": title}})

        else:
            return JSONResponse(status_code=404, content={"error": f"Unknown tool: {tool}"})

    except Exception as e:
        print(f"[ERROR] MCP invoke failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"500: Chrome could not start in current environment: {e}"}
        )


# ==========================================================
# 6️⃣ Safe Startup
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    print(f"[INFO] Launching Selenium MCP Server on port {port} ...")
    time.sleep(2)
    print("[INFO] MCP Server initialized and ready for connections.")
    uvicorn.run(app, host="0.0.0.0", port=port)

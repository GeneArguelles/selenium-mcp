#!/usr/bin/env python3
# ============================================================
# server.py — Render-safe Selenium MCP Server
# ============================================================

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# FastAPI app initialization
# ============================================================

app = FastAPI(title="Selenium MCP Server")

start_time = time.time()
last_invocation = "No tool executed yet."


# ============================================================
# Initialize Chrome driver using WebDriverManager
# ============================================================

def init_chrome_driver():
    """
    Initialize headless Chrome in a Render-safe environment.
    Uses WebDriverManager to ensure a matching ChromeDriver.
    """
    chrome_opts = Options()
    chrome_opts.binary_location = "/usr/bin/google-chrome"
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-software-rasterizer")
    chrome_opts.add_argument("--window-size=1920,1080")

    try:
        print("[INFO] Launching headless Chrome with WebDriverManager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_opts)
        print("[INFO] Chrome successfully started.")
        return driver
    except Exception as e:
        print(f"[ERROR] Chrome failed to start: {e}")
        raise RuntimeError(f"500: Chrome could not start in current environment: {e}")


# ============================================================
# MCP Endpoints
# ============================================================

@app.get("/")
async def root():
    return {"message": "Selenium MCP Server is running on Render."}


@app.get("/mcp/ping")
async def mcp_ping():
    return {"status": "ok"}


@app.post("/mcp/schema")
async def mcp_schema():
    return {
        "version": "2025-10-01",
        "server_info": {
            "type": "mcp",
            "name": "selenium_mcp_server",
            "description": "Render-hosted MCP exposing a headless browser automation tool.",
            "version": "1.0.0",
            "runtime": "3.11.9",
        },
        "tools": [
            {
                "name": "selenium_open_page",
                "description": "Open a URL in a headless Chrome browser and return the page title.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            }
        ],
    }


@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    global last_invocation
    try:
        body = await request.json()
        tool = body.get("tool")
        args = body.get("arguments", {})

        if tool == "selenium_open_page":
            url = args.get("url")
            if not url:
                return JSONResponse(
                    {"detail": "Missing required argument: 'url'"}, status_code=400
                )

            driver = init_chrome_driver()
            driver.get(url)
            title = driver.title
            driver.quit()

            last_invocation = f"selenium_open_page → {url}"
            return {"ok": True, "url": url, "title": title}

        return JSONResponse({"detail": f"Unknown tool: {tool}"}, status_code=400)

    except Exception as e:
        last_invocation = f"Failed: {e}"
        return JSONResponse(
            {"detail": f"500: Chrome could not start in current environment: {e}"},
            status_code=500,
        )


@app.get("/mcp/status")
async def mcp_status():
    uptime = round(time.time() - start_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "last_invocation": last_invocation,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ============================================================
# Launch entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("[INFO] Launching MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=10000)

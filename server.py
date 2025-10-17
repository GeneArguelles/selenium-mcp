#!/usr/bin/env python3
# ==========================================================
# Selenium MCP Server — Dual-use (Render + Local)
# ==========================================================
import os
import time
import platform
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# ----------------------------------------------------------
# 1️⃣ Environment Setup
# ----------------------------------------------------------
load_dotenv()  # Load from .env if present

PORT = int(os.getenv("PORT", 8000))
MCP_NAME = os.getenv("MCP_NAME", "Selenium")
MCP_DESCRIPTION = os.getenv("MCP_DESCRIPTION", "MCP server providing headless browser automation via Selenium.")
MCP_VERSION = os.getenv("MCP_VERSION", "1.0.0")
CHROME_PATH = os.getenv("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
HEADLESS = os.getenv("HEADLESS", "1") == "1"

app = FastAPI(title=MCP_NAME)

# ----------------------------------------------------------
# 2️⃣ Startup Logging
# ----------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("==========================================================")
    print(f"[INFO] Starting Selenium MCP Server...")
    print(f"[INFO] Description: {MCP_DESCRIPTION}")
    print(f"[INFO] Version: {MCP_VERSION}")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_PATH}")
    print(f"[INFO] PORT: {PORT}")
    print("==========================================================")
    time.sleep(1.0)

# ----------------------------------------------------------
# 3️⃣ Root Endpoint
# ----------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "running",
        "message": f"{MCP_NAME} MCP Server is live.",
        "runtime": platform.python_version(),
        "chrome_path": CHROME_PATH,
    }

# ----------------------------------------------------------
# 4️⃣ /mcp/schema (GET + POST)
# ----------------------------------------------------------
@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema(request: Request = None):
    schema = {
        "version": "2025-10-01",
        "type": "mcp",
        "server_info": {
            "name": MCP_NAME,
            "description": MCP_DESCRIPTION,
            "version": MCP_VERSION,
            "runtime": platform.python_version(),
        },
        "capabilities": {
            "invocation": True,
            "streaming": False,
            "multi_tool": False
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
    print(f"[INFO] Served /mcp/schema for {MCP_NAME} (Agent Builder compatible)")
    return JSONResponse(content=schema)

@app.get("/mcp/schema")
async def mcp_schema_get():
    return await mcp_schema()

# ----------------------------------------------------------
# 5️⃣ /mcp/invoke — Execute a Tool
# ----------------------------------------------------------
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    try:
        data = await request.json()
        tool = data.get("tool")
        args = data.get("arguments", {})

        if tool != "selenium_open_page":
            return JSONResponse(status_code=400, content={"detail": f"Unknown tool: {tool}"})

        url = args.get("url")
        if not url:
            return JSONResponse(status_code=400, content={"detail": "Missing 'url' argument."})

        print(f"[INFO] Launching headless Chrome for URL: {url}")

        chrome_options = Options()
        if HEADLESS:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-user")
        chrome_options.add_argument(f"--remote-debugging-port=9222")

        # Dynamic Chrome binary and driver version matching
        chrome_options.binary_location = CHROME_PATH
        chrome_version = "120.0.6099.18"  # fallback known-good
        try:
            service = Service(ChromeDriverManager(version=chrome_version).install())
        except Exception as e:
            print(f"[WARN] Falling back to auto ChromeDriverManager: {e}")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(15)
        driver.get(url)
        title = driver.title
        driver.quit()

        print(f"[INFO] Page loaded: {title}")
        return JSONResponse(content={"result": {"url": url, "title": title}})

    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse(status_code=500, content={"detail": f"500: Chrome could not start in current environment: {e}"})


# ----------------------------------------------------------
# 6️⃣ Server Startup
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("[INFO] Launching MCP Server...")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT)

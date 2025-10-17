#!/usr/bin/env python3
"""
server.py — Render-safe & Local-ready Selenium MCP Server
---------------------------------------------------------
Provides a Model Context Protocol (MCP) endpoint that exposes
Selenium browser automation to OpenAI Agent Builder or local tools.
"""

import os
import time
import platform
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# ==========================================================
# 1️⃣ Load environment variables
# ==========================================================
load_dotenv()  # Enables .env support for local development

MCP_NAME = os.getenv("MCP_NAME", "Selenium")
MCP_DESCRIPTION = os.getenv(
    "MCP_DESCRIPTION", "MCP server providing headless browser automation via Selenium."
)
MCP_VERSION = os.getenv("MCP_VERSION", "1.0.0")
CHROME_PATH = os.getenv("CHROME_PATH", "/opt/render/project/src/.local/chrome/chrome-linux/chrome")
PORT = int(os.getenv("PORT", "10000"))

# ==========================================================
# 2️⃣ Initialize FastAPI app
# ==========================================================
app = FastAPI(title=MCP_NAME)
startup_time = time.time()

# ==========================================================
# 3️⃣ Root endpoint for Render health checks
# ==========================================================
@app.get("/")
async def root():
    uptime = round(time.time() - startup_time, 2)
    msg = (
        f"🚀 {MCP_NAME} MCP Server is running\n"
        f"Description: {MCP_DESCRIPTION}\n"
        f"Version: {MCP_VERSION}\n"
        f"Python Runtime: {platform.python_version()}\n"
        f"Chrome Path: {CHROME_PATH}\n"
        f"Uptime: {uptime}s\n"
    )
    return PlainTextResponse(msg)

# ==========================================================
# 4️⃣ MCP Ping endpoint
# ==========================================================
@app.get("/mcp/ping")
async def mcp_ping():
    return {"status": "ok"}

# ==========================================================
# 5️⃣ MCP Status endpoint
# ==========================================================
@app.get("/mcp/status")
async def mcp_status():
    uptime = round(time.time() - startup_time, 2)
    return {
        "status": "running",
        "uptime_seconds": uptime,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chrome_path": CHROME_PATH,
        "python_runtime": platform.python_version(),
    }

# ==========================================================
# 6️⃣ MCP Schema endpoint (dynamic)
# ==========================================================
@app.api_route("/mcp/schema", methods=["GET", "POST"])
async def mcp_schema():
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "name": MCP_NAME,
            "description": MCP_DESCRIPTION,
            "version": MCP_VERSION,
            "runtime": platform.python_version(),
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
    print(f"[INFO] Served /mcp/schema for {MCP_NAME} (runtime={platform.python_version()})")
    return JSONResponse(content=schema)

# ==========================================================
# 7️⃣ MCP Invoke endpoint — executes Selenium tool
# ==========================================================
@app.post("/mcp/invoke")
async def mcp_invoke(request: Request):
    payload = await request.json()
    tool = payload.get("tool")
    args = payload.get("arguments", {})

    if tool != "selenium_open_page":
        return JSONResponse({"detail": f"Unknown tool: {tool}"}, status_code=400)

    url = args.get("url")
    if not url:
        return JSONResponse({"detail": "Missing required argument: url"}, status_code=400)

    print(f"[INFO] Invoking selenium_open_page on: {url}")

    # Configure Chrome options for headless execution
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = CHROME_PATH

    try:
        # ==============================================================
        # 🔍 Detect Chrome version dynamically (robust multi-path lookup)
        # ==============================================================
        chrome_candidates = [
            CHROME_PATH,
            "/opt/render/project/src/.local/chrome/chrome-linux/chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]

        chrome_major_version = None
        for candidate in chrome_candidates:
            try:
                if os.path.exists(candidate):
                    version_str = subprocess.check_output(
                        [candidate, "--version"], stderr=subprocess.STDOUT
                    ).decode("utf-8").strip()
                    # Example output: "Chromium 120.0.6099.18"
                    chrome_major_version = version_str.split()[1].split(".")[0]
                    print(f"[INFO] Using Chrome binary {candidate} ({version_str})")
                    break
            except Exception as e:
                print(f"[WARN] Failed version check for {candidate}: {e}")
                continue

        if not chrome_major_version:
            print("[WARN] Could not determine Chrome version — falling back to default driver.")
            driver_path = ChromeDriverManager().install()
        else:
            driver_path = ChromeDriverManager(version=f"{chrome_major_version}.0.0").install()
            print(f"[INFO] Installed ChromeDriver for version {chrome_major_version}")

        # Launch browser
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        title = driver.title
        driver.quit()

        print(f"[SUCCESS] Loaded {url} -> '{title}'")
        return JSONResponse({"result": {"url": url, "title": title}})

    except Exception as e:
        error_msg = f"500: Chrome could not start in current environment: {e}"
        print(f"[ERROR] {error_msg}")
        return JSONResponse({"detail": error_msg}, status_code=500)

# ==========================================================
# 8️⃣ Startup logs for Render
# ==========================================================
@app.on_event("startup")
async def startup_event():
    print("==========================================================")
    print(f"[INFO] Starting {MCP_NAME} MCP Server...")
    print(f"[INFO] Description: {MCP_DESCRIPTION}")
    print(f"[INFO] Version: {MCP_VERSION}")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_PATH}")
    print("==========================================================")

# ==========================================================
# 9️⃣ Run the server (for local debugging)
# ==========================================================
if __name__ == "__main__":
    import uvicorn

    print(f"[INFO] Launching MCP server on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

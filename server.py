# ==========================================================
# server.py — Selenium MCP Server (Render + Local Ready)
# ==========================================================

import os
import platform
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# ==========================================================
# 1️⃣ Environment Setup
# ==========================================================
load_dotenv()
APP_START_TIME = time.time()

app = FastAPI(title="Selenium MCP Server")

# ==========================================================
# 2️⃣ Explicit OPTIONS handler (must come before middleware)
# ==========================================================
@app.options("/mcp/schema")
def preflight_schema():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=204, headers=headers)

# ==========================================================
# 3️⃣ CORS Middleware
# ==========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Access-Control-Allow-Origin"],
    allow_credentials=False,
    max_age=86400,
)

# ==========================================================
# 4️⃣ Environment Variable Handling
# ==========================================================
SERVER_NAME = os.getenv("SERVER_NAME", "Selenium")
SERVER_DESC = os.getenv(
    "SERVER_DESC", "MCP server providing headless browser automation via Selenium."
)
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"

if LOCAL_MODE:
    CHROME_BINARY = os.getenv(
        "LOCAL_CHROME_BINARY", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    CHROMEDRIVER_PATH = os.getenv("LOCAL_CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
else:
    CHROME_BINARY = os.getenv(
        "CHROME_BINARY", "/opt/render/project/src/.local/chrome/chrome-linux/chrome"
    )
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "./chromedriver/chromedriver")

# Validate Chrome binary presence
if not os.path.exists(CHROME_BINARY):
    print(f"[WARN] Chrome binary not found at {CHROME_BINARY}. Attempting fallback...")
    fallback_path = "/usr/bin/google-chrome"
    if os.path.exists(fallback_path):
        CHROME_BINARY = fallback_path
        print(f"[INFO] ✅ Using fallback Chrome binary: {CHROME_BINARY}")
    else:
        print(f"[ERROR] ❌ No valid Chrome binary found.")
else:
    print(f"[INFO] ✅ Chrome binary confirmed: {CHROME_BINARY}")

# ==========================================================
# 5️⃣ Health Endpoint
# ==========================================================
@app.get("/health")
def health_check():
    uptime = round(time.time() - APP_START_TIME, 2)
    chrome_ok = os.path.exists(CHROME_BINARY)
    return {
        "status": "healthy" if chrome_ok else "unhealthy",
        "phase": "ready",
        "uptime_seconds": uptime,
        "chrome_path": CHROME_BINARY,
    }

# ==========================================================
# 6️⃣ MCP Schema and Invocation Models
# ==========================================================
class SchemaResponse(BaseModel):
    version: str
    type: str
    server_info: dict
    tools: list


class InvokeRequest(BaseModel):
    tool: str
    arguments: dict

# ==========================================================
# 7️⃣ /mcp/schema Endpoint
# ==========================================================
@app.post("/mcp/schema")
def get_schema():
    print("[INFO] Served /mcp/schema for Selenium (Agent Builder spec compliant)")
    schema = {
        "version": "2025-10-01",
        "type": "mcp_server",
        "server_info": {
            "type": "mcp_server",
            "name": SERVER_NAME,
            "description": SERVER_DESC,
            "version": "1.0.0",
            "runtime": platform.python_version(),
            "capabilities": {
                "invocation": True,
                "streaming": False,
                "multi_tool": False,
            },
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
    headers = {"Access-Control-Allow-Origin": "*"}
    return JSONResponse(content=schema, headers=headers)

# ==========================================================
# 8️⃣ /mcp/invoke Endpoint
# ==========================================================
@app.post("/mcp/invoke")
def invoke_tool(request: InvokeRequest):
    if request.tool == "selenium_open_page":
        url = request.arguments.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL argument.")

        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        try:
            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            title = driver.title
            driver.quit()
            return {"result": f"Opened {url}", "title": title}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chrome could not start: {e}")

    raise HTTPException(status_code=404, detail=f"Unknown tool: {request.tool}")

# ==========================================================
# 9️⃣ Startup Event + Diagnostics
# ==========================================================
@app.on_event("startup")
def on_startup():
    print("==========================================================")
    print("[INFO] Starting Selenium MCP Server...")
    print(f"[INFO] Description: {SERVER_DESC}")
    print(f"[INFO] Version: 1.0.0")
    print(f"[INFO] Python Runtime: {platform.python_version()}")
    print(f"[INFO] Chrome Binary: {CHROME_BINARY}")
    print(f"[INFO] ChromeDriver Path: {CHROMEDRIVER_PATH}")
    print("==========================================================")
    print("[INFO] Selenium MCP startup complete.")

# ==========================================================
# 10️⃣ Uvicorn Entrypoint (for Render)
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "10000"))
    print(f"[INFO] 🚀 Launching Uvicorn server on 0.0.0.0:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")

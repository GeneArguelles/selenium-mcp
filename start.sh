#!/usr/bin/env bash
# ==========================================================
# start.sh — Runtime start script for Selenium MCP
# ==========================================================

echo "[INFO] Starting Selenium MCP startup sequence..."

# 1️⃣ Install Chrome/ChromeDriver at runtime
bash install_chrome_runtime.sh

# 2️⃣ Print environment info
echo "[INFO] Environment Summary:"
echo "  🧩 Python: $(python3 --version)"
echo "  🧩 Node: $(node --version 2>/dev/null || echo 'none')"
echo "  🧩 Current Working Directory: $(pwd)"
echo "  🧩 PATH: $PATH"

# 3️⃣ Launch FastAPI via uvicorn
echo "[INFO] Launching MCP Server..."
exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}

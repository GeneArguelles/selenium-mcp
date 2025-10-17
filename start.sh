#!/usr/bin/env bash
# ==========================================================
# start.sh — Selenium MCP Auto-Healing Launcher
# ==========================================================

set -e

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load .env if available
# ----------------------------------------------------------
if [ -f .env ]; then
  echo "[INFO] Loading .env environment variables..."
  set -a
  source .env
  set +a
else
  echo "[WARN] No .env file found — proceeding with defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Run ChromeDriver auto-installer
# ----------------------------------------------------------
if [ -f "./install_chromedriver.sh" ]; then
  echo "[INFO] Running ChromeDriver installer (initial)..."
  bash ./install_chromedriver.sh
else
  echo "[ERROR] install_chromedriver.sh not found!"
  exit 1
fi

# ----------------------------------------------------------
# 3️⃣ Verify ChromeDriver executable
# ----------------------------------------------------------
if [ -x "./chromedriver/chromedriver" ]; then
  echo "[INFO] ChromeDriver binary found:"
  ./chromedriver/chromedriver --version || echo "[WARN] Version check failed (non-Linux platform)"
else
  echo "[ERROR] ChromeDriver missing after install — attempting reinstall..."
  bash ./install_chromedriver.sh
fi

# ----------------------------------------------------------
# 4️⃣ Start the MCP server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &
SERVER_PID=$!

# Allow warmup
sleep 5

# ----------------------------------------------------------
# 5️⃣ Verify MCP Server Health
# ----------------------------------------------------------
PORT=${PORT:-10000}
if curl -s "http://localhost:$PORT/mcp/schema" >/dev/null 2>&1; then
  echo "[INFO] MCP server successfully launched on port $PORT"
else
  echo "[WARN] MCP server not responding — possible ChromeDriver failure"
  echo "[INFO] Attempting ChromeDriver auto-heal..."
  bash ./install_chromedriver.sh
  echo "[INFO] Relaunching MCP server..."
  kill $SERVER_PID 2>/dev/null || true
  python3 server.py &
fi

# ----------------------------------------------------------
# 6️⃣ Keep process alive
# ----------------------------------------------------------
echo "=========================================================="
echo "[INFO] Selenium MCP fully initialized and monitored."
echo "[INFO] Auto-heal enabled for ChromeDriver mismatches."
echo "=========================================================="

wait

#!/usr/bin/env bash
set -e

# ==========================================================
#  Selenium MCP Server - Render Startup Script
# ==========================================================

START_TIME=$(date +%s)

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment
# ----------------------------------------------------------
echo "[INFO] Loading .env environment variables..."
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "[WARN] .env file not found — continuing with environment defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Log rotation
# ----------------------------------------------------------
mkdir -p logs
MAX_LOGS=3
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEPLOY_LOG="${LOG_DIR}/deploy_${TIMESTAMP}"
mkdir -p "$DEPLOY_LOG"
ls -dt ${LOG_DIR}/deploy_* 2>/dev/null | tail -n +$((MAX_LOGS + 1)) | xargs -r rm -rf
echo "[INFO] Logs rotated. Active folder: ${DEPLOY_LOG}"

# ----------------------------------------------------------
# 3️⃣ Detect Render environment
# ----------------------------------------------------------
if [[ "$RENDER" == "true" ]]; then
  echo "[☁️] Running in Render (server) mode ..."
else
  echo "[💻] Running in Local mode ..."
fi

# ----------------------------------------------------------
# 4️⃣ ChromeDriver auto-installation
# ----------------------------------------------------------
echo "[INFO] Starting ChromeDriver auto-installer..."
CHROME_VERSION=${CHROME_VERSION:-120.0.6099.18}
OS_ARCH=$(uname -m)
DOWNLOAD_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"

mkdir -p chromedriver
wget -q -O /tmp/chromedriver.zip "$DOWNLOAD_URL"
unzip -qo /tmp/chromedriver.zip -d chromedriver
rm -f /tmp/chromedriver.zip
chmod +x chromedriver/chromedriver

echo "[INFO] ✅ ChromeDriver installation complete!"
chromedriver/chromedriver --version || true

# ----------------------------------------------------------
# 5️⃣ Verify Chrome binary
# ----------------------------------------------------------
CHROME_BINARY=${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}
if [ -x "$CHROME_BINARY" ]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[ERROR] ❌ Chrome binary missing or not executable at $CHROME_BINARY"
fi

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &
SERVER_PID=$!

# ----------------------------------------------------------
# 7️⃣ Wait for Uvicorn / FastAPI to come online
# ----------------------------------------------------------
echo "[INFO] Waiting 10s for Uvicorn to initialize..."
sleep 10

# ----------------------------------------------------------
# 8️⃣ Final Health Summary
# ----------------------------------------------------------
PORT=${PORT:-10000}
HEALTH_URL="http://127.0.0.1:${PORT}/health"
echo "----------------------------------------------------------"
if curl -s --max-time 5 "$HEALTH_URL" | grep -q '"status": "healthy"'; then
  ELAPSED=$(( $(date +%s) - START_TIME ))
  echo "[✅ HEALTHY] MCP is running (phase: ready, uptime: ${ELAPSED}s)"
  echo "[CHROME] $CHROME_BINARY"
else
  echo "[⚠️ WARN] MCP health check still failing after retries."
  echo "[CHROME] $CHROME_BINARY"
  echo "[INFO] Keeping process alive for Render supervisor..."
fi
echo "----------------------------------------------------------"
echo "[INFO] MCP Startup Completed."
echo "=========================================================="

# ----------------------------------------------------------
# 9️⃣ Keep container alive (non-fatal exit)
# ----------------------------------------------------------
wait $SERVER_PID || true

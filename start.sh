#!/usr/bin/env bash
set -e

# ==========================================================
# start.sh — Unified MCP Startup Script (v4.0)
# ==========================================================

START_TIME=$(date +%s)
echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment variables
# ----------------------------------------------------------
echo "[INFO] Loading .env environment variables..."
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
else
  echo "[WARN] .env file not found — using defaults."
fi

DEPLOY_DIR="logs/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"

# ----------------------------------------------------------
# 2️⃣ Log rotation (keep last 3)
# ----------------------------------------------------------
echo "[INFO] Rotating logs (keeping last 3)..."
mkdir -p logs
cd logs
ls -1dt deploy_* 2>/dev/null | tail -n +4 | xargs -r rm -rf || true
cd ..
echo "[INFO] Logs rotated. Active folder: $DEPLOY_DIR"

# ----------------------------------------------------------
# 3️⃣ Environment context
# ----------------------------------------------------------
if [ "${LOCAL_MODE,,}" = "true" ]; then
  echo "[💻] Running in Local (macOS) mode ..."
  CHROME_BINARY="${LOCAL_CHROME_BINARY:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
else
  echo "[☁️] Running in Render (server) mode ..."
  CHROME_BINARY="${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}"
fi

# ----------------------------------------------------------
# 4️⃣ ChromeDriver Installer (self-healing)
# ----------------------------------------------------------
echo "[INFO] Starting ChromeDriver auto-installer..."
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  PLATFORM="mac-arm64"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  PLATFORM="mac-x64"
else
  PLATFORM="linux64"
fi

CHROME_VERSION=${CHROME_VERSION:-120.0.6099.18}
ZIP_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/${PLATFORM}/chromedriver-${PLATFORM}.zip"

mkdir -p chromedriver
curl -sSL "$ZIP_URL" -o /tmp/chromedriver.zip
unzip -qo /tmp/chromedriver.zip -d /tmp/chromedriver_pkg
mv -f /tmp/chromedriver_pkg/chromedriver*/chromedriver ./chromedriver/chromedriver
chmod +x ./chromedriver/chromedriver
rm -rf /tmp/chromedriver.zip /tmp/chromedriver_pkg
echo "[INFO] ✅ ChromeDriver installation complete!"
./chromedriver/chromedriver --version || true

# ----------------------------------------------------------
# 5️⃣ Chrome binary validation
# ----------------------------------------------------------
if [ -x "$CHROME_BINARY" ]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[WARN] Chrome binary not found at $CHROME_BINARY — attempting fallback..."
  FALLBACK="/usr/bin/google-chrome"
  if [ -x "$FALLBACK" ]; then
    CHROME_BINARY="$FALLBACK"
    echo "[INFO] ✅ Using fallback Chrome binary: $CHROME_BINARY"
  else
    echo "[ERROR] ❌ No valid Chrome binary found. Continuing but MCP may fail."
  fi
fi

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server (background)
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py >"$DEPLOY_DIR/mcp.log" 2>&1 &
SERVER_PID=$!

# Wait until port is open (max 30s)
PORT=${PORT:-10000}
echo "[INFO] Waiting for port ${PORT} to open..."
for i in {1..30}; do
  if nc -z 127.0.0.1 $PORT 2>/dev/null; then
    echo "[INFO] Port ${PORT} is now open (after ${i}s)."
    break
  fi
  sleep 1
done

# ----------------------------------------------------------
# 7️⃣ Health Retry Loop (non-fatal)
# ----------------------------------------------------------
HEALTH_URL="http://127.0.0.1:${PORT}/health"
RETRIES=5
SLEEP_INTERVAL=4
FAIL_COUNT=0

for i in $(seq 1 $RETRIES); do
  echo "[INFO] Checking MCP health (attempt ${i}/${RETRIES})..."
  if curl -s --max-time 5 "$HEALTH_URL" | grep -q '"status": "healthy"'; then
    echo "[✅ HEALTHY] MCP responded successfully."
    break
  else
    echo "[WARN] MCP not ready yet, retrying in ${SLEEP_INTERVAL}s..."
    ((FAIL_COUNT++))
    sleep "$SLEEP_INTERVAL"
  fi
done

# ----------------------------------------------------------
# 8️⃣ Final Health Summary
# ----------------------------------------------------------
echo "----------------------------------------------------------"
if curl -s "$HEALTH_URL" | grep -q '"status": "healthy"'; then
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

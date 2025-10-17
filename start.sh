#!/usr/bin/env bash
# ==========================================================
# start.sh — Unified startup manager for Selenium MCP Server
# ==========================================================

set -e
START_TIME=$(date +%s)

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load Environment
# ----------------------------------------------------------
if [ -f ".env" ]; then
  echo "[INFO] Loading .env environment variables..."
  set -a
  source .env
  set +a
else
  echo "[WARN] .env file not found, using defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Rotate Logs
# ----------------------------------------------------------
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
MAX_LOGS=3

count=$(ls -1 "$LOG_DIR" | wc -l 2>/dev/null || echo 0)
if [ "$count" -ge "$MAX_LOGS" ]; then
  ls -1t "$LOG_DIR" | tail -n +$((MAX_LOGS + 1)) | xargs -r -I {} rm -rf "$LOG_DIR/{}"
fi

DEPLOY_DIR="$LOG_DIR/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"
echo "[INFO] Logs rotated. Active folder: $DEPLOY_DIR"

# ----------------------------------------------------------
# 3️⃣ Mode Detection
# ----------------------------------------------------------
if [ "${LOCAL_MODE,,}" = "true" ]; then
  echo "[💻] Running in LOCAL_MODE (macOS) ..."
else
  echo "[☁️] Running in Render (server) mode ..."
fi

# ----------------------------------------------------------
# 4️⃣ ChromeDriver Installation
# ----------------------------------------------------------
install_chromedriver() {
  echo "[INFO] Starting ChromeDriver auto-installer..."
  mkdir -p chromedriver
  ARCH=$(uname -m)
  OS_TYPE=$(uname)
  echo "[INFO] Detected ${OS_TYPE} ${ARCH}"

  if [ "${LOCAL_MODE,,}" = "true" ]; then
    echo "[INFO] Skipping ChromeDriver install (LOCAL_MODE)"
    return
  fi

  DRIVER_VERSION="${CHROME_VERSION:-120.0.6099.18}"
  ZIP_URL="https://storage.googleapis.com/chrome-for-testing-public/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip"

  echo "[INFO] Download URL: ${ZIP_URL}"
  wget -q "$ZIP_URL" -O /tmp/chromedriver.zip
  unzip -q -o /tmp/chromedriver.zip -d chromedriver/
  chmod +x chromedriver/chromedriver

  echo "[INFO] ✅ ChromeDriver installation complete!"
  chromedriver/chromedriver --version || echo "[WARN] Unable to run chromedriver binary version check."
}

# ----------------------------------------------------------
# 5️⃣ Chrome Binary Validation
# ----------------------------------------------------------
validate_chrome_binary() {
  if [ "${LOCAL_MODE,,}" = "true" ]; then
    export CHROME_BINARY="${LOCAL_CHROME_BINARY:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
  else
    export CHROME_BINARY="${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}"
  fi

  if [ -x "$CHROME_BINARY" ]; then
    echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
  else
    echo "[ERROR] ❌ Chrome binary not found at $CHROME_BINARY"
    if [ "${LOCAL_MODE,,}" != "true" ]; then
      echo "[INFO] Attempting Chrome reinstallation..."
      mkdir -p /opt/render/project/src/.local/chrome
      wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux.zip" -O /tmp/chrome-linux.zip
      unzip -q /tmp/chrome-linux.zip -d /opt/render/project/src/.local/chrome/
      chmod +x /opt/render/project/src/.local/chrome/chrome-linux/chrome
      export CHROME_BINARY="/opt/render/project/src/.local/chrome/chrome-linux/chrome"
      echo "[INFO] ✅ Chrome reinstalled and path exported."
    fi
  fi
}

install_chromedriver
validate_chrome_binary

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server (background, non-blocking)
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py >"$DEPLOY_DIR/mcp.log" 2>&1 &
SERVER_PID=$!
sleep 8  # warm-up delay

# ----------------------------------------------------------
# 7️⃣ Health Retry Loop (non-fatal)
# ----------------------------------------------------------
HEALTH_URL="http://127.0.0.1:10000/health"
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
  echo "[✅ HEALTHY] MCP is running (phase: ready, uptime: $(($(date +%s) - START_TIME))s)"
  echo "[CHROME] $CHROME_BINARY"
else
  echo "[⚠️ WARN] MCP health check still failing after retries."
  echo "[CHROME] $CHROME_BINARY"
  echo "[INFO] Continuing anyway so Render stays alive..."
fi
echo "----------------------------------------------------------"
echo "[INFO] MCP Startup Completed."
echo "=========================================================="

# keep process running
wait $SERVER_PID || true

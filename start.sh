#!/bin/bash
# ==========================================================
# start.sh — Selenium MCP Render Startup Script
# ==========================================================
set -e

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment variables
# ----------------------------------------------------------
echo "[INFO] Loading .env environment variables..."
set -a
source .env 2>/dev/null || true
set +a

# Ensure Chrome binary paths are quoted properly
CHROME_BINARY="${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}"
CHROMEDRIVER_PATH="${CHROMEDRIVER_PATH:-./chromedriver/chromedriver}"
PORT="${PORT:-10000}"
RUN_VALIDATION="${RUN_VALIDATION:-false}"

# ----------------------------------------------------------
# 2️⃣ Log rotation setup
# ----------------------------------------------------------
echo "[INFO] Rotating logs (keeping last 3)..."
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
find "$LOG_DIR" -maxdepth 1 -type d -name "deploy_*" -printf '%T@ %p\n' 2>/dev/null | sort -n | head -n -3 | cut -d' ' -f2 | xargs -r rm -rf
DEPLOY_LOG="$LOG_DIR/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_LOG"
echo "[INFO] Logs rotated. Active folder: $DEPLOY_LOG"

# ----------------------------------------------------------
# 3️⃣ Environment diagnostics
# ----------------------------------------------------------
if [[ -n "$RENDER" ]]; then
  echo "[☁️] Running in Render (server) mode ..."
else
  echo "[💻] Running in Local mode ..."
fi


# ----------------------------------------------------------
# 4️⃣ ChromeDriver setup (Render-safe, no Python dependency)
# ----------------------------------------------------------
echo "[INFO] Checking ChromeDriver binary..."

if [[ -f "$CHROMEDRIVER_PATH" ]]; then
  echo "[INFO] ✅ ChromeDriver binary already present at $CHROMEDRIVER_PATH"
else
  echo "[WARN] ChromeDriver not found — performing manual installation..."
  mkdir -p "$(dirname "$CHROMEDRIVER_PATH")"
  CHROME_VERSION=${CHROME_VERSION:-120.0.6099.18}
  DOWNLOAD_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
  echo "[INFO] Download URL: $DOWNLOAD_URL"
  curl -L "$DOWNLOAD_URL" -o chromedriver.zip
  unzip -o chromedriver.zip -d "$(dirname "$CHROMEDRIVER_PATH")"
  rm chromedriver.zip
  echo "[INFO] ✅ ChromeDriver installed manually at $CHROMEDRIVER_PATH"
fi

if [[ ! -f "$CHROMEDRIVER_PATH" ]]; then
  echo "[ERROR] ❌ ChromeDriver still not found at $CHROMEDRIVER_PATH"
  exit 1
fi


# ----------------------------------------------------------
# 5️⃣ Validate Chrome binary
# ----------------------------------------------------------
if [[ -f "$CHROME_BINARY" ]]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[WARN] Chrome binary not found at $CHROME_BINARY"
fi

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &
SERVER_PID=$!

# ----------------------------------------------------------
# 7️⃣ Wait for Uvicorn port (10000) to open
# ----------------------------------------------------------
echo "[INFO] Waiting for MCP server to report READY..."
for i in {1..10}; do
  if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
    echo "[INFO] MCP reported READY (after ${i}s)."
    break
  fi
  sleep 1
done

# ----------------------------------------------------------
# 8️⃣ Health check loop
# ----------------------------------------------------------
HEALTH_URL="http://127.0.0.1:${PORT}/health"
MAX_RETRIES=5
RETRY_DELAY=4
SUCCESS=false

for ((i=1; i<=MAX_RETRIES; i++)); do
  echo "[INFO] Checking MCP health (attempt $i/$MAX_RETRIES)..."
  STATUS=$(curl -s "$HEALTH_URL" | jq -r '.status // empty')
  if [[ "$STATUS" == "healthy" ]]; then
    echo "[✅ HEALTHY] MCP is running (phase: ready)"
    SUCCESS=true
    break
  fi
  echo "[WARN] MCP not ready yet, retrying in ${RETRY_DELAY}s..."
  sleep "$RETRY_DELAY"
done

if [[ "$SUCCESS" == "false" ]]; then
  echo "[⚠️ WARN] MCP health check still failing after retries."
fi

# ----------------------------------------------------------
# 9️⃣ Optional validation step
# ----------------------------------------------------------
if [[ "$RUN_VALIDATION" == "true" ]]; then
  echo "----------------------------------------------------------"
  echo "[INFO] Running post-deploy validation (validate_mcp.sh)..."
  if [[ -f "./validate_mcp.sh" ]]; then
    bash ./validate_mcp.sh || {
      echo "[ERROR] ❌ Validation failed — exiting."
      exit 1
    }
    echo "[✅] MCP validation complete."
  else
    echo "[WARN] Skipping validation — validate_mcp.sh not found."
  fi
  echo "----------------------------------------------------------"
else
  echo "[INFO] RUN_VALIDATION=false — skipping MCP validation."
fi

# ----------------------------------------------------------
# 🔟 Keep container alive for Render supervisor
# ----------------------------------------------------------
echo "=========================================================="
echo "[INFO] MCP Startup Completed."
echo "=========================================================="
wait $SERVER_PID || true

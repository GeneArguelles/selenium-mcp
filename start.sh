#!/usr/bin/env bash
# ==========================================================
# start.sh — Unified startup script for Selenium MCP
# Local + Render compatible (self-healing)
# ==========================================================

set -e

# ANSI colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m" # No color

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load .env (if exists)
# ----------------------------------------------------------
if [ -f .env ]; then
  echo "[INFO] Loading .env environment variables..."
  set -a
  source .env || true
  set +a
else
  echo "[WARN] .env file not found — using defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Log rotation (Render-safe)
# ----------------------------------------------------------
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
ts=$(date +"%Y%m%d_%H%M%S")
DEPLOY_DIR="${LOG_DIR}/deploy_${ts}"
mkdir -p "${DEPLOY_DIR}"
echo "[INFO] Rotating logs (keeping last 3)..."
find "$LOG_DIR" -mindepth 1 -maxdepth 1 -type d -name "deploy_*" | sort | head -n -3 | xargs -I {} rm -rf "{}"
echo "[INFO] Logs rotated. Active folder: ${DEPLOY_DIR}"

# ----------------------------------------------------------
# 3️⃣ Determine runtime mode
# ----------------------------------------------------------
LOCAL_MODE="${LOCAL_MODE:-false}"

if [ "$LOCAL_MODE" = true ]; then
  echo "[INFO] 🧩 LOCAL_MODE enabled — using macOS Chrome paths"
else
  echo "[INFO] ☁️ Running in Render (server) mode"
fi

# ----------------------------------------------------------
# 4️⃣ Local Mode — Self-healing Chrome setup
# ----------------------------------------------------------
if [ "$LOCAL_MODE" = true ]; then
  INSTALLER="./mac_install_chromefortesting.sh"

  if [ ! -x "$INSTALLER" ]; then
    echo "[WARN] mac_install_chromefortesting.sh not found — creating stub..."
    echo "#!/bin/bash" > "$INSTALLER"
    echo "echo '[WARN] Installer script missing — please restore mac_install_chromefortesting.sh'" >> "$INSTALLER"
    chmod +x "$INSTALLER"
  fi

  # Check if Chrome + ChromeDriver exist
  if [ ! -f "${LOCAL_CHROME_PATH}" ] || [ ! -f "${LOCAL_CHROMEDRIVER_PATH}" ]; then
    echo "[WARN] Chrome or ChromeDriver not found — running installer..."
    bash "$INSTALLER"
  else
    echo "[INFO] ✅ Local Chrome + ChromeDriver already installed."
  fi
fi

# ----------------------------------------------------------
# 5️⃣ Render Mode — Ensure ChromeDriver exists
# ----------------------------------------------------------
if [ "$LOCAL_MODE" = false ]; then
  echo "[INFO] Running ChromeDriver installer (Render environment)..."
  bash ./install_chromedriver.sh || echo "[WARN] Render ChromeDriver setup failed (may retry later)."
fi

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &

PID=$!
sleep 2

# ----------------------------------------------------------
# 7️⃣ Health Check Loop
# ----------------------------------------------------------
RETRY_COUNT=0
MAX_RETRIES=3
PORT="${PORT:-10000}"
HEALTH_URL="http://127.0.0.1:${PORT}/health"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  sleep 2
  echo "[INFO] Checking MCP health (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
  if curl -fs "$HEALTH_URL" >/dev/null; then
    echo "[INFO] ✅ MCP Server is healthy."
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT+1))
done

# ----------------------------------------------------------
# 8️⃣ Auto-recover if MCP is unresponsive
# ----------------------------------------------------------
if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "[WARN] MCP health check failed — attempting ChromeDriver rebuild..."
  bash ./install_chromedriver.sh || true
  sleep 3
  echo "[INFO] Relaunching MCP Server..."
  python3 server.py &
  PID=$!
fi

# ----------------------------------------------------------
# 9️⃣ Final Health Summary (color-coded)
# ----------------------------------------------------------
echo "----------------------------------------------------------"
echo "[INFO] Performing final health summary check..."
HEALTH_JSON=$(curl -s "$HEALTH_URL" || echo "{}")
STATUS=$(echo "$HEALTH_JSON" | jq -r '.status // empty')
PHASE=$(echo "$HEALTH_JSON" | jq -r '.phase // empty')
CHROME_PATH=$(echo "$HEALTH_JSON" | jq -r '.chrome_path // empty')
UPTIME=$(echo "$HEALTH_JSON" | jq -r '.uptime_seconds // empty')

if [ "$STATUS" = "healthy" ]; then
  echo -e "${GREEN}[✅ HEALTHY] MCP is running (phase: $PHASE, uptime: ${UPTIME}s)${NC}"
  echo -e "${GREEN}[CHROME] $CHROME_PATH${NC}"
elif [ "$STATUS" = "recovering" ]; then
  echo -e "${YELLOW}[⚠️ RECOVERING] MCP partially responsive (phase: $PHASE)${NC}"
  echo -e "${YELLOW}[CHROME] $CHROME_PATH${NC}"
else
  echo -e "${RED}[❌ UNHEALTHY] MCP did not start properly.${NC}"
  echo -e "${RED}[CHROME] Path unavailable or invalid.${NC}"
fi

echo "----------------------------------------------------------"
echo "[INFO] MCP Startup Completed."
echo "=========================================================="

# ----------------------------------------------------------
# 🔁 Keep container running (Render)
# ----------------------------------------------------------
wait $PID || true

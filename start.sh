#!/usr/bin/env bash
# ==========================================================
# start.sh — Selenium MCP Launcher with Auto-Heal, Healthcheck, and Log Rotation
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

PORT=${PORT:-10000}
FAIL_COUNT=0
MAX_RETRIES=2
HEALTH_RETRIES=3
LOG_DIR="/opt/render/project/src/logs"
mkdir -p "$LOG_DIR"

# ----------------------------------------------------------
# 2️⃣ Rotate logs — keep last 3 deployments
# ----------------------------------------------------------
echo "[INFO] Rotating logs (keeping last 3)..."
cd "$LOG_DIR"
timestamp=$(date +"%Y%m%d_%H%M%S")
DEPLOY_DIR="deploy_${timestamp}"
mkdir -p "$DEPLOY_DIR"
cd - >/dev/null

mv "$LOG_DIR"/*.log "$LOG_DIR"/*_chromedriver.log "$LOG_DIR"/*server.log "$LOG_DIR"/*diagnostic.log "$DEPLOY_DIR"/ 2>/dev/null || true
cd "$LOG_DIR"
ls -dt deploy_* 2>/dev/null | tail -n +4 | xargs -r rm -rf
cd - >/dev/null
echo "[INFO] Logs rotated. Active folder: $DEPLOY_DIR"

# ----------------------------------------------------------
# 3️⃣ ChromeDriver Installer
# ----------------------------------------------------------
if [ -f "./install_chromedriver.sh" ]; then
  echo "[INFO] Running ChromeDriver installer (initial)..."
  bash ./install_chromedriver.sh | tee "$LOG_DIR/install_chromedriver.log"
else
  echo "[ERROR] install_chromedriver.sh not found!"
  exit 1
fi

# ----------------------------------------------------------
# 4️⃣ Verify ChromeDriver executable
# ----------------------------------------------------------
if [ -x "./chromedriver/chromedriver" ]; then
  echo "[INFO] ChromeDriver binary found:"
  ./chromedriver/chromedriver --version || echo "[WARN] Version check failed (non-Linux platform)"
else
  echo "[ERROR] ChromeDriver missing after install — attempting reinstall..."
  bash ./install_chromedriver.sh | tee -a "$LOG_DIR/install_chromedriver.log"
fi

# ----------------------------------------------------------
# 5️⃣ Start MCP Server Function
# ----------------------------------------------------------
start_server() {
  echo "[INFO] Launching MCP Server..."
  python3 server.py > "$LOG_DIR/server.log" 2>&1 &
  SERVER_PID=$!
  sleep 6

  if curl -sf "http://localhost:$PORT/mcp/schema" >/dev/null 2>&1; then
    echo "[INFO] MCP server responding on /mcp/schema."
    return 0
  else
    echo "[WARN] MCP server not responding to schema check."
    return 1
  fi
}

# ----------------------------------------------------------
# 6️⃣ /health Retry Function
# ----------------------------------------------------------
check_health() {
  local retries=0
  while [ $retries -lt $HEALTH_RETRIES ]; do
    echo "[INFO] Checking /health endpoint (attempt $((retries + 1))/$HEALTH_RETRIES)..."
    if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
      echo "[INFO] /health check passed."
      return 0
    else
      echo "[WARN] /health check failed."
      retries=$((retries + 1))
      sleep 5
    fi
  done

  echo "[ERROR] /health check failed after $HEALTH_RETRIES attempts."
  return 1
}

# ----------------------------------------------------------
# 7️⃣ Main Launch Loop with Auto-Heal + Diagnostics
# ----------------------------------------------------------
while [ $FAIL_COUNT -le $MAX_RETRIES ]; do
  if start_server; then
    echo "[INFO] MCP startup successful. Checking /health..."
    if check_health; then
      echo "[INFO] MCP passed /health verification — service healthy."
      break
    else
      ((FAIL_COUNT++))
      echo "[WARN] /health failed — attempting ChromeDriver reinstall..."
      bash ./install_chromedriver.sh | tee -a "$LOG_DIR/install_chromedriver.log"
      echo "[INFO] Restarting MCP server..."
      kill $SERVER_PID 2>/dev/null || true
    fi
  else
    ((FAIL_COUNT++))
    echo "[ERROR] Attempt #$FAIL_COUNT failed to start MCP."
    if [ $FAIL_COUNT -le $MAX_RETRIES ]; then
      echo "[INFO] Running ChromeDriver auto-heal (reinstall)..."
      bash ./install_chromedriver.sh | tee -a "$LOG_DIR/install_chromedriver.log"
      echo "[INFO] Restarting MCP server..."
      kill $SERVER_PID 2>/dev/null || true
    else
      echo "[FATAL] Maximum retries ($MAX_RETRIES) reached. Capturing diagnostics..."
      echo "==========================================================" | tee "$LOG_DIR/diagnostic.log"
      echo "[INFO] Dumping ChromeDriver logs..." | tee -a "$LOG_DIR/diagnostic.log"
      if [ -f chromedriver/chromedriver.log ]; then
        cat chromedriver/chromedriver.log | tee -a "$LOG_DIR/diagnostic.log"
      else
        echo "[WARN] chromedriver.log not found." | tee -a "$LOG_DIR/diagnostic.log"
      fi
      if [ -f /tmp/chrome-debug.log ]; then
        echo "[INFO] Dumping /tmp/chrome-debug.log" | tee -a "$LOG_DIR/diagnostic.log"
        cat /tmp/chrome-debug.log | tee -a "$LOG_DIR/diagnostic.log"
      else
        echo "[WARN] /tmp/chrome-debug.log not found." | tee -a "$LOG_DIR/diagnostic.log"
      fi
      echo "[INFO] Logs stored in $LOG_DIR/diagnostic.log"
      echo "[INFO] Exiting for post-mortem review."
      echo "=========================================================="
      exit 1
    fi
  fi
done

# ----------------------------------------------------------
# 8️⃣ Keep Process Alive for Container Persistence
# ----------------------------------------------------------
echo "=========================================================="
echo "[INFO] Selenium MCP fully initialized and monitored."
echo "[INFO] Auto-heal + /health monitor + log rotation active."
echo "=========================================================="

wait

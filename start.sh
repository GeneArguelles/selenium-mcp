#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# 1️⃣ Load environment
if [ -f .env ]; then
  echo "[INFO] Loading environment variables from .env safely..."
  set -a
  source .env
  set +a
else
  echo "[WARN] No .env found — using system defaults."
fi

# 2️⃣ Rotate logs
LOG_DIR="logs/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "[INFO] Logs rotated. Active folder: $LOG_DIR"

# 3️⃣ Check Chrome binaries
if [ -f "./chromedriver/chromedriver" ]; then
  echo "[INFO] ✅ ChromeDriver binary present at ./chromedriver/chromedriver"
else
  echo "[ERROR] ❌ ChromeDriver not found!"
  exit 1
fi

if [ -f "/opt/render/project/src/.local/chrome/chrome-linux/chrome" ]; then
  echo "[INFO] ✅ Chrome binary confirmed: /opt/render/project/src/.local/chrome/chrome-linux/chrome"
else
  echo "[WARN] ⚠️ Chrome binary not found — using local path"
fi

# 4️⃣ Launch MCP Server
echo "[INFO] Launching MCP Server via Uvicorn on port ${PORT:-10000}..."
nohup python3 server.py >"$LOG_DIR/mcp.log" 2>&1 &

# 5️⃣ Wait for health
echo "[INFO] Waiting for MCP health..."
for i in {1..10}; do
  sleep 1
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT:-10000}/health || true)
  if [ "$STATUS" == "200" ]; then
    echo "[✅ HEALTHY] MCP is running (uptime: ${i}s)"
    break
  fi
  echo "[INFO] Attempt ${i}/10: not ready (HTTP $STATUS)"
done

# 6️⃣ Final diagnostics
echo "[CHROME] /opt/render/project/src/.local/chrome/chrome-linux/chrome"
echo "=========================================================="
echo "[INFO] RUN_VALIDATION=${RUN_VALIDATION} — skipping MCP validation."
echo "[INFO] MCP process active — following logs."

tail -n 50 -f "$LOG_DIR/mcp.log"

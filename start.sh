#!/usr/bin/env bash
set -e

# ==========================================================
# 🧩 Selenium MCP — Render Startup Script
# Version: 2025.10.20a
# ==========================================================

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment variables
# ----------------------------------------------------------
if [ -f .env ]; then
  echo "[INFO] Loading environment variables from .env safely..."
  set -o allexport
  source .env
  set +o allexport
else
  echo "[WARN] No .env file found — proceeding with defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Log rotation (keep last 3 deploy logs)
# ----------------------------------------------------------
mkdir -p logs
ts=$(date +"%Y%m%d_%H%M%S")
find logs -type f -name "deploy_*" | sort | head -n -3 | xargs -r rm -f
log_dir="logs/deploy_${ts}"
mkdir -p "$log_dir"
echo "[INFO] Logs rotated. Active folder: ${log_dir}"

# ----------------------------------------------------------
# 3️⃣ ChromeDriver + Chrome binary checks
# ----------------------------------------------------------
CHROME_BINARY=${CHROME_BINARY:-"/opt/render/project/src/.local/chrome/chrome-linux/chrome"}
CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-"./chromedriver/chromedriver"}

if [[ -f "$CHROMEDRIVER_PATH" ]]; then
  echo "[INFO] ✅ ChromeDriver binary present at $CHROMEDRIVER_PATH"
else
  echo "[ERROR] ❌ ChromeDriver not found at $CHROMEDRIVER_PATH"
  exit 1
fi

if [[ -f "$CHROME_BINARY" ]]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[ERROR] ❌ Chrome binary not found: $CHROME_BINARY"
  exit 1
fi

# ----------------------------------------------------------
# 4️⃣ Launch Uvicorn MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server via Uvicorn on port 10000..."
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 10000 > "${log_dir}/uvicorn.log" 2>&1 &
UVICORN_PID=$!

# ----------------------------------------------------------
# 5️⃣ Health polling — wait until /health responds 200
# ----------------------------------------------------------
echo "[INFO] Waiting for MCP health..."
for i in {1..10}; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:10000/health || true)
  if [ "$status" = "200" ]; then
    echo "[✅ HEALTHY] MCP is running (uptime: ${i}s)"
    break
  else
    echo "[INFO] Waiting for MCP health (attempt ${i}/10)..."
    sleep 2
  fi
done

if [ "$status" != "200" ]; then
  echo "[⚠️ WARN] MCP health check still failing after 10 attempts."
else
  echo "[CHROME] $CHROME_BINARY"
fi

# ----------------------------------------------------------
# 6️⃣ Optional validation suite
# ----------------------------------------------------------
if [ "$RUN_VALIDATION" = "true" ]; then
  echo "[INFO] Running MCP validation suite (validate_mcp.sh)..."
  if [ -f "./validate_mcp.sh" ]; then
    chmod +x ./validate_mcp.sh
    ./validate_mcp.sh || echo "[WARN] Validation script detected issues — continuing."
  else
    echo "[WARN] validate_mcp.sh not found; skipping."
  fi
else
  echo "[INFO] RUN_VALIDATION=false — skipping MCP validation."
fi

# ----------------------------------------------------------
# 7️⃣ ✅ Run diagnostics suite (NEW)
# ----------------------------------------------------------
if [ "$RUN_DIAGNOSTICS" = "true" ]; then
  echo "[INFO] Running MCP diagnostics suite (diagnose_mcp_runtime.sh)..."
  if [ -f "./diagnose_mcp_runtime.sh" ]; then
    chmod +x ./diagnose_mcp_runtime.sh
    ./diagnose_mcp_runtime.sh || echo "[WARN] Diagnostics reported issues — see logs above."
  else
    echo "[WARN] diagnose_mcp_runtime.sh not found; skipping diagnostics."
  fi
else
  echo "[INFO] RUN_DIAGNOSTICS=false — skipping diagnostics."
fi

# ----------------------------------------------------------
# 8️⃣ Keep MCP process alive (Render supervisor)
# ----------------------------------------------------------
echo "[INFO] MCP process active — following logs."
tail -f "${log_dir}/uvicorn.log"

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

# 5️⃣ Wait for local server to be ready
echo "[INFO] Waiting for MCP local health check..."
for i in {1..15}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT:-10000}/mcp/schema || true)
  if [ "$STATUS" == "200" ]; then
    echo "[✅ READY] MCP schema available locally after ${i}s"
    break
  fi
  echo "[WAIT] Attempt ${i}/15: not ready (HTTP $STATUS). Retrying..."
  sleep 2
done

# ==========================================================
# 🧩 MCP Remote Warmup (GET only to avoid schema POST issues)
# ==========================================================
WARMUP_URL="https://selenium-mcp.onrender.com/mcp/schema"
MAX_ATTEMPTS=10
DELAY=3
LATENCIES=()

echo "=========================================================="
echo "[WARMUP] Warming MCP endpoint: $WARMUP_URL"
echo "=========================================================="

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  echo "[WARMUP] Attempt $i/$MAX_ATTEMPTS → GET $WARMUP_URL"
  RESULT=$(curl -s -o /tmp/warmup_response.json -w "%{http_code} %{time_total}" "$WARMUP_URL")
  STATUS=$(echo "$RESULT" | awk '{print $1}')
  LATENCY=$(echo "$RESULT" | awk '{print $2}')
  LATENCIES+=("$LATENCY")
  echo "  → HTTP $STATUS | ${LATENCY}s"

  if [[ "$STATUS" == "200" ]]; then
    echo "✅ [WARMUP] Remote MCP schema warmed successfully."
    break
  fi

  echo "❌ [WARMUP] Not ready (HTTP $STATUS). Retrying in ${DELAY}s..."
  sleep $DELAY
done

# Summary
AVG_LAT=$(printf '%s\n' "${LATENCIES[@]}" | awk '{sum+=$1} END {if (NR>0) printf "%.3f", sum/NR; else print "N/A"}')
echo "----------------------------------------------------------"
echo "[WARMUP] Average schema GET latency: ${AVG_LAT}s"
echo "[WARMUP] MCP warmup complete."
echo "=========================================================="

# 6️⃣ Final diagnostics
echo "[INFO] MCP deployment complete and fully warmed."
echo "[INFO] Logs: $LOG_DIR/mcp.log"
echo "=========================================================="

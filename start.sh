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

# ==========================================================
# 🧩 MCP Auto-Warmup + Latency Analytics (GET + POST)
# Simulates Agent Builder handshake and warms up /mcp/schema
# ==========================================================
WARMUP_URL="https://selenium-mcp.onrender.com/mcp/schema"
MAX_ATTEMPTS=10
DELAY=3
GET_LATENCIES=()
POST_LATENCIES=()

echo "=========================================================="
echo "[WARMUP] Initiating MCP endpoint warmup (GET + POST)..."
echo "=========================================================="

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  echo "[WARMUP] Attempt $i/$MAX_ATTEMPTS → $WARMUP_URL"

  # ---- GET Test ----
  RESULT_GET=$(curl -s -o /tmp/warmup_get.json -w "%{http_code} %{time_total}" "$WARMUP_URL")
  STATUS_GET=$(echo "$RESULT_GET" | awk '{print $1}')
  LAT_GET=$(echo "$RESULT_GET" | awk '{print $2}')
  GET_LATENCIES+=("$LAT_GET")
  echo "  [GET]  HTTP $STATUS_GET | ${LAT_GET}s"

  # ---- POST Test ----
  RESULT_POST=$(curl -s -X POST -H "Content-Type: application/json" \
      -o /tmp/warmup_post.json -w "%{http_code} %{time_total}" \
      -d '{}' "$WARMUP_URL")
  STATUS_POST=$(echo "$RESULT_POST" | awk '{print $1}')
  LAT_POST=$(echo "$RESULT_POST" | awk '{print $2}')
  POST_LATENCIES+=("$LAT_POST")
  echo "  [POST] HTTP $STATUS_POST | ${LAT_POST}s"

  # ---- Success condition ----
  if [[ "$STATUS_GET" == "200" || "$STATUS_POST" == "200" ]]; then
    echo "✅ [WARMUP] MCP schema warmed successfully at $(date)"
    echo "----------------------------------------------------------"
    TOOLS_COUNT=$(jq '.tools | length' /tmp/warmup_post.json 2>/dev/null)
    echo "[WARMUP] Tools detected in schema: $TOOLS_COUNT"
    jq -r '.tools[].name' /tmp/warmup_post.json 2>/dev/null | \
      xargs -I{} echo "[WARMUP] → Tool: {}"
    echo "=========================================================="
    break
  else
    echo "❌ [WARMUP] Endpoint not ready (GET=$STATUS_GET, POST=$STATUS_POST). Retrying in ${DELAY}s..."
    sleep $DELAY
  fi
done

# ---- Latency Summary ----
AVG_GET=$(printf '%s\n' "${GET_LATENCIES[@]}" | awk '{sum+=$1} END {if (NR>0) printf "%.3f", sum/NR; else print "N/A"}')
AVG_POST=$(printf '%s\n' "${POST_LATENCIES[@]}" | awk '{sum+=$1} END {if (NR>0) printf "%.3f", sum/NR; else print "N/A"}')

echo "----------------------------------------------------------"
echo "[WARMUP] Average Latency Summary:"
echo "  GET  → ${AVG_GET}s over ${#GET_LATENCIES[@]} attempts"
echo "  POST → ${AVG_POST}s over ${#POST_LATENCIES[@]} attempts"
echo "----------------------------------------------------------"

if [[ "$STATUS_GET" != "200" && "$STATUS_POST" != "200" ]]; then
  echo "[WARMUP] ⚠️ MCP schema endpoint not ready after ${MAX_ATTEMPTS} attempts."
  echo "[WARMUP] This may cause temporary 502 errors until Render fully warms."
fi
echo "=========================================================="

# 5️⃣ Wait for local health check
echo "[INFO] Waiting for MCP local health..."
for i in {1..10}; do
  sleep 1
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT:-10000}/health || true)
  if [ "$STATUS" == "200" ]; then
    echo "[✅ HEALTHY] MCP is running locally (uptime: ${i}s)"
    break
  fi
  echo "[INFO] Attempt ${i}/10: not ready (HTTP $STATUS)"
done

# 6️⃣ Final diagnostics
echo "=========================================================="
echo "[INFO] MCP deployment complete and warming initiated."
echo "[INFO] Logs: $LOG_DIR/mcp.log"
echo "=========================================================="

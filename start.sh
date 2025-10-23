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
CHROME_PATH="/opt/render/project/src/.local/chrome/chrome-linux/chrome"
CHROMEDRIVER_PATH="./chromedriver/chromedriver"

if [ -f "$CHROMEDRIVER_PATH" ]; then
  echo "[INFO] ✅ ChromeDriver binary present at $CHROMEDRIVER_PATH"
else
  echo "[ERROR] ❌ ChromeDriver not found!"
  exit 1
fi

if [ -f "$CHROME_PATH" ]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_PATH"
else
  echo "[WARN] ⚠️ Chrome binary not found — using fallback local path"
fi

# 4️⃣ Launch MCP Server using uvicorn with Render PORT binding
echo "[INFO] Launching MCP Server via Uvicorn on port ${PORT:-10000}..."
nohup uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}" >"$LOG_DIR/mcp.log" 2>&1 &

# 5️⃣ Warmup: Auto-ping MCP /mcp/schema endpoint to reduce cold-start latency
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

  RESULT_GET=$(curl -s -o /tmp/warmup_get.json -w "%{http_code} %{time_total}" "$WARMUP_URL")
  STATUS_GET=$(echo "$RESULT_GET" | awk '{print $1}')
  LAT_GET=$(echo "$RESULT_GET" | awk '{print $2}')
  GET_LATENCIES+=("$LAT_GET")
  echo "  [GET]  HTTP $STATUS_GET | ${LAT_GET}s"

  RESULT_POST=$(curl -s -X POST -H "Content-Type: application/json" \
    -o /tmp/warmup_post.json -w "%{http_code} %{time_total}" -d '{}' "$WARMUP_URL")
  STATUS_POST=$(echo "$RESULT_POST" | awk '{print $1}')
  LAT_POST=$(echo "$RESULT_POST" | awk '{print $2}')
  POST_LATENCIES+=("$LAT_POST")
  echo "  [POST] HTTP $STATUS_POST | ${LAT_POST}s"

  if [[ "$STATUS_GET" == "200" || "$STATUS_POST" == "200" ]]; then
    echo "✅ [WARMUP] MCP schema warmed successfully at $(date)"
    jq '.manifest.tools | length' /tmp/warmup_post.json 2>/dev/null | \
      xargs -I{} echo "[WARMUP] Tools detected in manifest: {}"
    break
  else
    echo "❌ [WARMUP] Not ready (GET=$STATUS_GET, POST=$STATUS_POST). Retrying in ${DELAY}s..."
    sleep "$DELAY"
  fi
done

# 6️⃣ Print warmup latency summary
if (( ${#GET_LATENCIES[@]} > 0 )); then
  AVG_GET=$(printf '%s\n' "${GET_LATENCIES[@]}" | awk '{sum+=$1} END {if (NR>0) printf "%.3f", sum/NR}')
else
  AVG_GET="N/A"
fi

if (( ${#POST_LATENCIES[@]} > 0 )); then
  AVG_POST=$(printf '%s\n' "${POST_LATENCIES[@]}" | awk '{sum+=$1} END {if (NR>0) printf "%.3f", sum/NR}')
else
  AVG_POST="N/A"
fi

echo "----------------------------------------------------------"
echo "[WARMUP] Average Latency Summary:"
echo "  GET  → ${AVG_GET}s over ${#GET_LATENCIES[@]} attempts"
echo "  POST → ${AVG_POST}s over ${#POST_LATENCIES[@]} attempts"
echo "----------------------------------------------------------"

if [[ "$STATUS_GET" != "200" && "$STATUS_POST" != "200" ]]; then
  echo "[WARMUP] ⚠️ MCP schema not ready after ${MAX_ATTEMPTS} attempts."
  echo "[WARMUP] This may cause initial 502s until container fully warms."
fi

# 7️⃣ Optional: Continuous keep-alive to prevent Render sleep (every 5 minutes)
# Comment this block out if you're on a paid Render plan or using external keep-alive pings
# echo "[KEEP-ALIVE] Starting background keep-alive pings every 5 min..."
# while true; do
#   curl -s "$WARMUP_URL" > /dev/null
#   sleep 300
# done

# 8️⃣ Final Diagnostic
echo "=========================================================="
echo "[INFO] MCP deployment complete and warming initiated."
echo "Logs: $LOG_DIR/mcp.log"
echo "=========================================================="

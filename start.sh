#!/usr/bin/env bash
# ==========================================================
# start.sh — Selenium MCP Server Startup Script (Render-Ready)
# ==========================================================
# Includes:
#   • Safe .env loader (handles spaces and quotes)
#   • Log rotation (retain last 3 deploy folders)
#   • Chrome + ChromeDriver validation and fallback installer
#   • Explicit Uvicorn launch for Render port detection
#   • Health-check polling with retries
#   • Optional post-startup validation via validate_mcp.sh
#   • Final “keep-alive” for Render supervisor
# ==========================================================

set -e  # Exit on first unhandled error
START_TIME=$(date +%s)

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Safe .env Loader (quoted and space-safe)
# ----------------------------------------------------------
if [ -f .env ]; then
  echo "[INFO] Loading environment variables from .env safely..."
  while IFS='=' read -r key value; do
    # Ignore comments or blank lines
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    # Remove surrounding quotes if present
    value="${value%\"}"
    value="${value#\"}"
    export "$key"="$value"
  done < .env
else
  echo "[WARN] .env not found — proceeding with defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Log Rotation (keep last 3)
# ----------------------------------------------------------
mkdir -p logs
ts=$(date +"%Y%m%d_%H%M%S")
deploy_dir="logs/deploy_${ts}"
mkdir -p "$deploy_dir"
# Delete all but last 3 deployments
find logs -maxdepth 1 -type d -name "deploy_*" | sort | head -n -3 | xargs -r rm -rf
echo "[INFO] Logs rotated. Active folder: $deploy_dir"

# ----------------------------------------------------------
# 3️⃣ Chrome Binary & Driver Verification
# ----------------------------------------------------------
CHROME_BINARY=${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}
CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-./chromedriver/chromedriver}

if [[ -f "$CHROMEDRIVER_PATH" ]]; then
  echo "[INFO] ✅ ChromeDriver binary present at $CHROMEDRIVER_PATH"
else
  echo "[INFO] Installing ChromeDriver via chromedriver-binary-auto..."
  pip install chromedriver-binary-auto || true
  python3 - <<'EOF'
try:
    from chromedriver_binary_auto import install
    install()
    print("[INFO] ✅ ChromeDriver installation complete.")
except Exception as e:
    print(f"[WARN] ChromeDriver install failed: {e}")
EOF
fi

if [[ -f "$CHROME_BINARY" ]]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[WARN] ⚠️ Chrome binary missing at $CHROME_BINARY — check path!"
fi

# ----------------------------------------------------------
# 4️⃣ Launch MCP Server via Uvicorn
# ----------------------------------------------------------
PORT=${PORT:-10000}
echo "[INFO] Launching MCP Server via Uvicorn on port $PORT..."
uvicorn server:app --host 0.0.0.0 --port "$PORT" --log-level info &
SERVER_PID=$!

# ----------------------------------------------------------
# 5️⃣ Wait for MCP Health Endpoint
# ----------------------------------------------------------
HEALTH_URL="http://127.0.0.1:${PORT}/health"
MAX_RETRIES=10
RETRY_DELAY=4
COUNT=0

+ until curl -s --max-time 3 "$HEALTH_URL" | jq -e '.status == "healthy"' >/dev/null 2>&1; do
+   COUNT=$((COUNT+1))
+   echo "[INFO] Waiting for MCP health (attempt $COUNT/$MAX_RETRIES)..."
+   sleep "$RETRY_DELAY"
+   if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
+     echo "[⚠️ WARN] MCP health check still failing after $MAX_RETRIES attempts."
+     break
+   fi
+ done
+
+ # ----------------------------------------------------------
+ # 6️⃣ Health Summary (jq-verified)
+ # ----------------------------------------------------------
+ if curl -s "$HEALTH_URL" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
+   ELAPSED=$(( $(date +%s) - START_TIME ))
+   echo "[✅ HEALTHY] MCP is running (uptime: ${ELAPSED}s)"
+ else
+   echo "[⚠️ WARN] MCP did not confirm healthy status (check endpoint output)."
+   echo "[DEBUG] Response was: $(curl -s "$HEALTH_URL")"
+ fi


# ----------------------------------------------------------
# 7️⃣ Optional Validation Phase
# ----------------------------------------------------------
if [ "${RUN_VALIDATION:-false}" = "true" ]; then
  echo "[INFO] RUN_VALIDATION=true — running validate_mcp.sh..."
  chmod +x validate_mcp.sh || true
  ./validate_mcp.sh || echo "[WARN] Validation failed (non-fatal)."
else
  echo "[INFO] RUN_VALIDATION=false — skipping MCP validation."
fi

# ----------------------------------------------------------
# 8️⃣ Keep Process Alive for Render Supervisor
# ----------------------------------------------------------
if ps -p "$SERVER_PID" >/dev/null 2>&1; then
  echo "[INFO] MCP process active — following logs."
  wait "$SERVER_PID"
else
  echo "[INFO] MCP process not detected — keeping container alive."
  tail -f /dev/null
fi

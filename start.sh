#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment (safe for values with spaces)
# ----------------------------------------------------------
if [ -f .env ]; then
  echo "[INFO] Loading environment variables from .env safely..."
  while IFS='=' read -r key value; do
    # Skip comment lines or blank lines
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    # Trim surrounding quotes if present
    value="${value%\"}"
    value="${value#\"}"
    export "$key"="$value"
  done < .env
else
  echo "[WARN] .env file not found — continuing with defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Rotate logs (keep last 3)
# ----------------------------------------------------------
mkdir -p logs
ts=$(date +"%Y%m%d_%H%M%S")
deploy_dir="logs/deploy_${ts}"
mkdir -p "$deploy_dir"
find logs -maxdepth 1 -type d -name "deploy_*" | sort | head -n -3 | xargs -r rm -rf
echo "[INFO] Logs rotated. Active folder: $deploy_dir"

# ----------------------------------------------------------
# 3️⃣ Chrome binary + driver check
# ----------------------------------------------------------
CHROME_BINARY=${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}
CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-./chromedriver/chromedriver}

if [[ -f "$CHROMEDRIVER_PATH" ]]; then
  echo "[INFO] ✅ ChromeDriver binary already present at $CHROMEDRIVER_PATH"
else
  echo "[INFO] Installing ChromeDriver..."
  pip install chromedriver-binary-auto || true
  python3 - <<'EOF'
from chromedriver_binary_auto import install
install()
EOF
fi

if [[ -f "$CHROME_BINARY" ]]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[WARN] ⚠️ Chrome binary not found at $CHROME_BINARY"
fi

# ----------------------------------------------------------
# 4️⃣ Launch MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &
SERVER_PID=$!

# ----------------------------------------------------------
# 5️⃣ Wait for Uvicorn /health to report healthy
# ----------------------------------------------------------
PORT=${PORT:-10000}
HEALTH_URL="http://127.0.0.1:${PORT}/health"
retries=10
count=0
until curl -s --max-time 3 "$HEALTH_URL" | grep -q '"status": "healthy"'; do
  count=$((count+1))
  echo "[INFO] Waiting for MCP health (attempt $count/$retries)..."
  sleep 4
  if [ "$count" -ge "$retries" ]; then
    echo "[⚠️ WARN] MCP health check still failing after retries."
    break
  fi
done

# ----------------------------------------------------------
# 6️⃣ Final summary
# ----------------------------------------------------------
if curl -s "$HEALTH_URL" | grep -q '"status": "healthy"'; then
  echo "[✅ HEALTHY] MCP is running."
else
  echo "[⚠️ WARN] MCP health check did not confirm healthy status."
fi
echo "[CHROME] $CHROME_BINARY"
echo "=========================================================="

# ----------------------------------------------------------
# 7️⃣ Optional validation (if enabled)
# ----------------------------------------------------------
if [ "${RUN_VALIDATION:-false}" = "true" ]; then
  echo "[INFO] RUN_VALIDATION=true — running validate_mcp.sh..."
  chmod +x validate_mcp.sh || true
  ./validate_mcp.sh || echo "[WARN] Validation script failed (non-fatal)."
else
  echo "[INFO] RUN_VALIDATION=false — skipping MCP validation."
fi

# ----------------------------------------------------------
# 8️⃣ Keep container alive (Render supervisor)
# ----------------------------------------------------------
if ps -p "$SERVER_PID" >/dev/null 2>&1; then
  wait "$SERVER_PID"
else
  tail -f /dev/null
fi

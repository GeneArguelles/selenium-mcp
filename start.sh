#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment
# ----------------------------------------------------------
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# ----------------------------------------------------------
# 2️⃣ Rotate logs
# ----------------------------------------------------------
mkdir -p logs
ts=$(date +"%Y%m%d_%H%M%S")
deploy_dir="logs/deploy_${ts}"
mkdir -p "$deploy_dir"
find logs -maxdepth 1 -type d -name "deploy_*" | sort | head -n -3 | xargs -r rm -rf
echo "[INFO] Logs rotated. Active folder: $deploy_dir"

# ----------------------------------------------------------
# 3️⃣ Chrome binaries check
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

echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"

# ----------------------------------------------------------
# 4️⃣ Launch MCP Server
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py &
SERVER_PID=$!

# ----------------------------------------------------------
# 5️⃣ Wait for Uvicorn health
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
# 7️⃣ Keep alive
# ----------------------------------------------------------
if ps -p "$SERVER_PID" >/dev/null 2>&1; then
  wait "$SERVER_PID"
else
  tail -f /dev/null
fi

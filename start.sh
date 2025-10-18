#!/usr/bin/env bash
# ==========================================================
# start.sh — Unified MCP Startup Script (Render + Local)
# ==========================================================

set -e
START_TIME=$(date +%s)
DEPLOY_DIR="logs/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"

echo "=========================================================="
echo "[INFO] Starting Selenium MCP startup sequence..."
echo "=========================================================="

# ----------------------------------------------------------
# 1️⃣ Load environment
# ----------------------------------------------------------
echo "[INFO] Loading .env environment variables..."
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] No .env file found — using defaults."
fi

# ----------------------------------------------------------
# 2️⃣ Rotate logs (keep last 3)
# ----------------------------------------------------------
echo "[INFO] Rotating logs (keeping last 3)..."
mkdir -p logs
ls -dt logs/deploy_* 2>/dev/null | tail -n +4 | xargs -r rm -rf
echo "[INFO] Logs rotated. Active folder: $DEPLOY_DIR"

# ----------------------------------------------------------
# 3️⃣ Environment detection
# ----------------------------------------------------------
if [ "${LOCAL_MODE}" = "true" ]; then
  echo "[💻] Running in Local mode ..."
else
  echo "[☁️] Running in Render (server) mode ..."
fi

# ----------------------------------------------------------
# 4️⃣ ChromeDriver installer
# ----------------------------------------------------------
echo "[INFO] Starting ChromeDriver auto-installer..."
python3 - <<'PYCODE'
import os, zipfile, urllib.request, pathlib

chrome_version = os.getenv("CHROME_VERSION", "120.0.6099.18")
arch = "linux64"
url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/{arch}/chromedriver-{arch}.zip"
target_dir = pathlib.Path("chromedriver")
target_dir.mkdir(exist_ok=True)
zip_path = target_dir / "chromedriver.zip"

print(f"[INFO] Download URL: {url}")
urllib.request.urlretrieve(url, zip_path)
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(target_dir)
zip_path.unlink()
print(f"[INFO] ✅ ChromeDriver installation complete!")
os.system("chromedriver/chromedriver --version")
PYCODE

# ----------------------------------------------------------
# 5️⃣ Chrome binary validation
# ----------------------------------------------------------
CHROME_BINARY=${CHROME_BINARY:-/opt/render/project/src/.local/chrome/chrome-linux/chrome}
if [ -x "$CHROME_BINARY" ]; then
  echo "[INFO] ✅ Chrome binary confirmed: $CHROME_BINARY"
else
  echo "[ERROR] ❌ Chrome binary missing or not executable: $CHROME_BINARY"
  exit 1
fi

# ----------------------------------------------------------
# 6️⃣ Launch MCP Server (background)
# ----------------------------------------------------------
echo "[INFO] Launching MCP Server..."
python3 server.py >"$DEPLOY_DIR/mcp.log" 2>&1 &
SERVER_PID=$!

# ----------------------------------------------------------
# 7️⃣ Wait for READY signal in log (max 45s)
# ----------------------------------------------------------
echo "[INFO] Waiting for MCP server to report READY..."
for i in {1..45}; do
  if grep -q "\[READY\]" "$DEPLOY_DIR/mcp.log"; then
    echo "[INFO] MCP reported READY (after ${i}s)."
    break
  fi
  sleep 1
done

# ----------------------------------------------------------
# 8️⃣ Final Health Summary
# ----------------------------------------------------------
PORT=${PORT:-10000}
HEALTH_URL="http://127.0.0.1:${PORT}/health"
echo "----------------------------------------------------------"
if curl -s --max-time 5 "$HEALTH_URL" | grep -q '"status": "healthy"'; then
  ELAPSED=$(( $(date +%s) - START_TIME ))
  echo "[✅ HEALTHY] MCP is running (phase: ready, uptime: ${ELAPSED}s)"
  echo "[CHROME] $CHROME_BINARY"
else
  echo "[⚠️ WARN] MCP health check still failing after retries."
  echo "[CHROME] $CHROME_BINARY"
  echo "[INFO] Keeping process alive for Render supervisor..."
fi
echo "----------------------------------------------------------"
echo "[INFO] MCP Startup Completed."
echo "=========================================================="

# ----------------------------------------------------------
# 9️⃣ Keep container alive (non-fatal exit)
# ----------------------------------------------------------
wait $SERVER_PID || true

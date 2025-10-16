#!/usr/bin/env bash
# ==========================================================
# start.sh — Render-safe startup script for Selenium MCP
# ==========================================================

echo "[INFO] Starting Selenium MCP startup sequence..."

# ----------------------------------------------------------
# 1️⃣ Check for Chromium binary
# ----------------------------------------------------------
echo "[INFO] Checking for Chromium binary..."
CHROMIUM_PATHS=(
  "/usr/bin/chromium"
  "/usr/bin/chromium-browser"
  "/opt/render/.local/share/pyppeteer/local-chromium/1181205/chrome-linux/chrome"
  "/tmp/chromium/chrome"
)
CHROMIUM_FOUND=""

for path in "${CHROMIUM_PATHS[@]}"; do
  if [ -x "$path" ]; then
    CHROMIUM_FOUND="$path"
    echo "[INFO] Found Chromium at: $CHROMIUM_FOUND"
    "$CHROMIUM_FOUND" --version || echo "[WARN] Could not determine Chromium version"
    break
  fi
done

if [ -z "$CHROMIUM_FOUND" ]; then
  echo "[WARN] No Chromium found in common paths. It will be downloaded automatically by pyppeteer."
fi

# ----------------------------------------------------------
# 2️⃣ Check for ChromeDriver binary
# ----------------------------------------------------------
echo "[INFO] Checking for ChromeDriver binary..."
CHROMEDRIVER_FOUND="$(which chromedriver 2>/dev/null)"
if [ -z "$CHROMEDRIVER_FOUND" ]; then
  if [ -x "/opt/render/project/src/.venv/bin/chromedriver" ]; then
    CHROMEDRIVER_FOUND="/opt/render/project/src/.venv/bin/chromedriver"
  fi
fi

if [ -n "$CHROMEDRIVER_FOUND" ]; then
  echo "[INFO] Found ChromeDriver at: $CHROMEDRIVER_FOUND"
else
  echo "[WARN] ChromeDriver not found — Selenium will attempt auto-download at runtime."
fi

# ----------------------------------------------------------
# 3️⃣ Print environment summary
# ----------------------------------------------------------
echo "[INFO] Environment Summary:"
echo "  🧩 Python: $(python3 --version)"
echo "  🧩 Node: $(node --version 2>/dev/null || echo 'none')"
echo "  🧩 Current Working Directory: $(pwd)"
echo "  🧩 PATH: $PATH"

# ----------------------------------------------------------
# 4️⃣ Start FastAPI/Uvicorn app
# ----------------------------------------------------------
echo "[INFO] Launching FastAPI server..."
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}"

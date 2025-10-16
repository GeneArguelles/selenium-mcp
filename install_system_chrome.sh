#!/usr/bin/env bash
# ======================================================
# install_system_chrome.sh — Render-safe user-space Chrome
# ======================================================

set -e
set -o pipefail

echo "[INFO] Installing Chromium (user-space)..."

CHROME_DIR="/opt/render/project/src/.local/chrome"
CHROME_ZIP="$CHROME_DIR/chrome-linux.zip"
CHROME_BIN="$CHROME_DIR/chrome-linux/chrome"
CHROME_URL="https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1213125/chrome-linux.zip"

mkdir -p "$CHROME_DIR"
cd "$CHROME_DIR"

# ------------------------------------------------------
# Step 1: Download chromium zip if not already cached
# ------------------------------------------------------
if [ -f "$CHROME_BIN" ]; then
  echo "[INFO] Existing Chromium binary found: $CHROME_BIN"
else
  echo "[INFO] Downloading Chromium from $CHROME_URL ..."
  curl -L "$CHROME_URL" -o "$CHROME_ZIP" --progress-bar || {
    echo "[ERROR] Failed to download Chromium archive."
    exit 1
  }

  echo "[INFO] Extracting Chromium..."
  unzip -q "$CHROME_ZIP" || {
    echo "[ERROR] Failed to unzip Chromium archive."
    exit 1
  }
  rm -f "$CHROME_ZIP"
fi

# ------------------------------------------------------
# Step 2: Verify binary presence
# ------------------------------------------------------
if [ -f "$CHROME_BIN" ]; then
  echo "[INFO] ✅ Chromium installed successfully at $CHROME_BIN"
else
  echo "[ERROR] ❌ Chromium binary not found after extraction!"
  exit 1
fi

# ------------------------------------------------------
# Step 3: Export env var for runtime
# ------------------------------------------------------
echo "export CHROME_BINARY=$CHROME_BIN" >> ~/.bashrc
echo "[INFO] CHROME_BINARY set to $CHROME_BIN"

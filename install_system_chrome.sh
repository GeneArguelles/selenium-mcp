#!/usr/bin/env bash
# ======================================================
# install_system_chrome.sh — Render-safe Chromium installer
# ------------------------------------------------------
# Installs a working headless Chromium binary into user-space
# (no apt-get, no root permissions)
# ======================================================

set -e
set -o pipefail

echo "[INFO] Installing Chromium (user-space)..."

CHROME_DIR="/opt/render/project/src/.local/chrome"
CHROME_ZIP="$CHROME_DIR/chrome-linux.zip"
CHROME_BIN="$CHROME_DIR/chrome-linux/chrome"
CHROME_MIRROR="https://commondatastorage.googleapis.com/chromium-browser-snapshots/Linux_x64/1213125/chrome-linux.zip"

mkdir -p "$CHROME_DIR"
cd "$CHROME_DIR"

# ------------------------------------------------------
# Step 1: Download Chromium archive
# ------------------------------------------------------
if [ -f "$CHROME_BIN" ]; then
  echo "[INFO] ✅ Existing Chromium binary found at $CHROME_BIN"
else
  echo "[INFO] Downloading Chromium from mirror..."
  curl -L -f -o "$CHROME_ZIP" "$CHROME_MIRROR" --progress-bar || {
    echo "[ERROR] ❌ Failed to download Chromium binary."
    exit 1
  }

  # Verify ZIP validity
  if unzip -tq "$CHROME_ZIP" >/dev/null 2>&1; then
    echo "[INFO] Zip integrity check passed."
  else
    echo "[ERROR] ❌ Invalid or partial zip — download corrupted!"
    rm -f "$CHROME_ZIP"
    exit 1
  fi

  echo "[INFO] Extracting Chromium..."
  unzip -q "$CHROME_ZIP" || {
    echo "[ERROR] ❌ Failed to unzip Chromium archive."
    exit 1
  }
  rm -f "$CHROME_ZIP"
fi

# ------------------------------------------------------
# Step 2: Verify binary
# ------------------------------------------------------
if [ -x "$CHROME_BIN" ]; then
  echo "[INFO] ✅ Chromium installed successfully at $CHROME_BIN"
  "$CHROME_BIN" --version || echo "[WARN] Chrome version check failed (but binary exists)."
else
  echo "[ERROR] ❌ Chromium binary missing or not executable!"
  exit 1
fi

# ------------------------------------------------------
# Step 3: Export env var for runtime
# ------------------------------------------------------
echo "export CHROME_BINARY=$CHROME_BIN" >> ~/.bashrc
echo "[INFO] Environment variable CHROME_BINARY set to $CHROME_BIN"

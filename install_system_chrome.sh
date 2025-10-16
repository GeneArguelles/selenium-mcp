#!/usr/bin/env bash
# ======================================================
# install_system_chrome.sh — Render-safe Chrome installer
# ======================================================
set -e

echo "[INFO] Installing Chromium (user-space)..."

# Create working directory
mkdir -p /opt/render/project/src/.local/chrome
cd /opt/render/project/src/.local/chrome

# Download precompiled Chromium for Linux
CHROME_URL="https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1213125/chrome-linux.zip"
wget -q $CHROME_URL -O chrome-linux.zip

# Extract to user-space
unzip -q chrome-linux.zip
rm chrome-linux.zip

# Verify binary
if [ -f "chrome-linux/chrome" ]; then
  echo "[INFO] Chromium installed at $(pwd)/chrome-linux/chrome"
else
  echo "[ERROR] Chromium binary missing!"
  exit 1
fi

# Export environment variable for runtime
echo "export CHROME_BINARY=/opt/render/project/src/.local/chrome/chrome-linux/chrome" >> ~/.bashrc
echo "[INFO] CHROME_BINARY set for runtime."

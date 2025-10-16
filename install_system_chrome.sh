#!/usr/bin/env bash
# ==========================================================
# install_system_chrome.sh — Install Google Chrome & ChromeDriver
# ==========================================================

set -e

echo "[INFO] Installing Google Chrome and ChromeDriver..."

# Prepare APT environment
apt-get update -y || echo "[WARN] apt-get update failed (Render sandbox may be readonly)"
apt-get install -y wget gnupg unzip curl || true

# Add Google Chrome’s official key and repo
if [ ! -f /etc/apt/sources.list.d/google-chrome.list ]; then
  wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-keyring.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
fi

# Install Chrome Stable and matching driver
apt-get update -y
apt-get install -y google-chrome-stable chromium-driver

echo "[INFO] Chrome version:"
google-chrome --version || echo "[WARN] Chrome not found after install."
echo "[INFO] ChromeDriver version:"
chromedriver --version || echo "[WARN] ChromeDriver not found after install."

#!/usr/bin/env bash
# ==========================================================
# install_system_chrome.sh — Prebuild script for Render
# Installs Google Chrome + ChromeDriver system-wide
# ==========================================================

set -e

echo "[INFO] Installing Google Chrome and ChromeDriver via APT..."

apt-get update
apt-get install -y wget gnupg unzip curl

# Add Google Chrome's official repo
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
  > /etc/apt/sources.list.d/google-chrome.list

apt-get update
apt-get install -y google-chrome-stable chromium-chromedriver

echo "[INFO] Installed Chrome:"
google-chrome --version
echo "[INFO] Installed ChromeDriver:"
chromedriver --version

echo "[INFO] Chrome installation complete."

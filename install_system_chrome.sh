#!/usr/bin/env bash
set -e
echo "[INFO] Installing Chromium from apt..."
apt-get update -y || echo "[WARN] apt-get update failed (maybe read-only FS)"
apt-get install -y chromium-browser chromium-chromedriver || echo "[WARN] apt-get install failed (Render may restrict apt)"

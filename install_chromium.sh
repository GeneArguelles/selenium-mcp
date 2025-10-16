#!/usr/bin/env bash
# ==========================================================
# install_chromium.sh — Prebuild cache + Chromium fetch
# ==========================================================
# Purpose: Ensure Chromium is preinstalled and cached in
#          /opt/render/.local/share/pyppeteer/local-chromium
# ==========================================================

set -e

CHROMIUM_DIR="/opt/render/.local/share/pyppeteer/local-chromium"
CHROMIUM_EXEC="$CHROMIUM_DIR/1181205/chrome-linux/chrome"

echo "[INFO] === Prebuild: Checking cached Chromium ==="

if [ -x "$CHROMIUM_EXEC" ]; then
  echo "[INFO] Cached Chromium found at: $CHROMIUM_EXEC"
  "$CHROMIUM_EXEC" --version || echo "[WARN] Cached Chromium version unknown."
else
  echo "[WARN] No cached Chromium detected. Triggering pyppeteer download..."
  mkdir -p "$CHROMIUM_DIR"
  python3 - <<'PYCODE'
import os
from pyppeteer import chromium_downloader

try:
    path = chromium_downloader.chromium_executable()
    print(f"[INFO] Chromium already available at {path}")
except Exception:
    print("[INFO] Downloading Chromium for pyppeteer...")
    chromium_downloader.download_chromium()
    path = chromium_downloader.chromium_executable()
    print(f"[INFO] Chromium downloaded to: {path}")
PYCODE
fi

echo "[INFO] === Chromium prebuild step complete ==="

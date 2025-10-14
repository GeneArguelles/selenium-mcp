#!/usr/bin/env bash
set -e

echo "[INFO] Installing Chromium at runtime..."
apt-get update && apt-get install -y chromium chromium-driver

echo "[INFO] Starting FastAPI server..."
exec uvicorn server:app --host 0.0.0.0 --port $PORT

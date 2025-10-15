#!/usr/bin/env bash
# start.sh — Runtime initialization for Render MCP Server

echo "[INFO] Installing Chromium runtime dependencies..."
apt-get update && apt-get install -y chromium chromium-common chromium-driver || echo "[WARN] Could not apt-install chromium, may already exist"

echo "[INFO] Starting FastAPI (Uvicorn) server..."
exec uvicorn server:app --host 0.0.0.0 --port $PORT

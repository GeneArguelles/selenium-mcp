#!/usr/bin/env bash
echo "[INFO] Starting Selenium MCP..."
exec uvicorn server:app --host 0.0.0.0 --port $PORT

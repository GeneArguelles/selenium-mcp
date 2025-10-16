#!/usr/bin/env bash
# ==========================================================
# start.sh — Render-safe startup for Playwright MCP Server
# ==========================================================

set -e
echo "[INFO] Starting Playwright MCP startup sequence..."

# ----------------------------------------------------------
# 1️⃣ Ensure Playwright Chromium is available
# ----------------------------------------------------------
echo "[INFO] Installing Playwright Chromium (if not cached)..."
python -m playwright install chromium --with-deps || true

# ----------------------------------------------------------
# 2️⃣ Print environment summary
# ----------------------------------------------------------
echo "[INFO] Environment Summary:"
echo "  🧩 Python: $(python3 --version)"
echo "  🧩 Node: $(node --version 2>/dev/null || echo 'none')"
echo "  🧩 Current Working Directory: $(pwd)"
echo "  🧩 PATH: $PATH"

# ----------------------------------------------------------
# 3️⃣ Start FastAPI Server
# ----------------------------------------------------------
echo "[INFO] Launching FastAPI (Uvicorn) server..."
exec uvicorn server:app --host 0.0.0.0 --port $PORT

#!/bin/bash
# ==========================================================
# force_refresh_mcp.sh — OpenAI Agent Builder Cache-Buster
# Version: 2025.10.19
# Author: Gene Arguelles
# ==========================================================
# This script generates a cache-busting URL for your MCP
# server and optionally verifies it is reachable.
# ==========================================================

# --- CONFIG ------------------------------------------------
MCP_BASE="https://selenium-mcp.onrender.com/live"
TMP_JSON="/tmp/mcp_check.json"

# --- LOGO --------------------------------------------------
echo "=========================================================="
echo " 🧩 MCP Agent Builder Cache-Buster"
echo "=========================================================="

# --- Generate a unique nonce (timestamp + random suffix) ---
NONCE=$(date +%s%N | sha1sum | cut -c1-8)
CACHEBUST_URL="${MCP_BASE}?nonce=${NONCE}"

echo "[INFO] Generated cache-busting URL:"
echo "       ${CACHEBUST_URL}"
echo "----------------------------------------------------------"

# --- Connectivity & schema sanity check --------------------
echo "[INFO] Verifying endpoint..."
curl -s -X POST -H "Cache-Control: no-cache" "${CACHEBUST_URL}" -o "$TMP_JSON"

TYPE=$(jq -r '.type // empty' "$TMP_JSON")
TOOLS=$(jq -r '.tools | length // 0' "$TMP_JSON")

if [[ "$TYPE" == "mcp" && "$TOOLS" -gt 0 ]]; then
  echo "✅ MCP manifest OK — type: $TYPE, tools: $TOOLS"
else
  echo "⚠️  MCP manifest check failed."
  jq . "$TMP_JSON"
fi

echo "----------------------------------------------------------"
echo "[NEXT] Paste this URL into Agent Builder when asked for"
echo "       the MCP endpoint:"
echo "       ${CACHEBUST_URL}"
echo "=========================================================="

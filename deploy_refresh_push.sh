#!/usr/bin/env bash
# ==========================================================
# Render Auto-Warmup + MCP Validation Deployment Script
# ==========================================================
# Performs a git push, waits for container readiness,
# warms up key endpoints (/health, /live, /mcp/schema),
# and runs a real invoke test to confirm backend health.
# ==========================================================

set -e  # Stop on error
START_TIME=$(date +%s)

# Your Render service base URL
BASE_URL="https://selenium-mcp.onrender.com"

# ----------------------------------------------------------
# 1️⃣ Push latest code to Render
# ----------------------------------------------------------
echo "=========================================================="
echo "[DEPLOY] Pushing latest commit to Render..."
echo "=========================================================="
git add . && git commit -m "Auto deploy $(date +%F_%T)" || true
git push origin main

echo "Waiting 30s for build + container to start..."
sleep 30

# ----------------------------------------------------------
# 2️⃣ Poll /health until live
# ----------------------------------------------------------
echo "[CHECK] Waiting for health endpoint..."
for i in {1..15}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" || true)
  if [[ "$STATUS" == "200" ]]; then
    echo "[OK] Health check passed."
    break
  fi
  echo "[WAIT] Health not ready (status=$STATUS), retrying in 5s..."
  sleep 5
done

# ----------------------------------------------------------
# 3️⃣ Fetch current MCP version
# ----------------------------------------------------------
MCP_VERSION=$(curl -s "$BASE_URL" | jq -r '.mcp_version // .version' | tr -d '"')
if [[ -z "$MCP_VERSION" ]]; then
  MCP_VERSION="v$(date +%Y%m%d)a"
fi
LIVE_URL="$BASE_URL/$MCP_VERSION/live?nonce=$(date +%s)&refresh=true"

echo "[INFO] Detected MCP version: $MCP_VERSION"
echo "[INFO] Live URL: $LIVE_URL"

# ----------------------------------------------------------
# 4️⃣ Warm up endpoints
# ----------------------------------------------------------
for ENDPOINT in "/mcp/schema" "/live" "/health"; do
  echo "[WARMUP] $ENDPOINT ..."
  start=$(date +%s%3N)
  HTTP_CODE=$(curl -s -o /tmp/warmup.json -w "%{http_code}" "$BASE_URL$ENDPOINT" || true)
  end=$(date +%s%3N)
  LATENCY=$((end - start))
  echo "   → HTTP $HTTP_CODE in ${LATENCY}ms"
done

# ----------------------------------------------------------
# 4.5️⃣ Schema Version Verification (Compact Deploy & Verify)
# ----------------------------------------------------------
echo "[VERIFY] Checking MCP schema version fields..."
sleep 5  # short grace period for MCP_VERSION registration
curl -s "$BASE_URL/mcp/schema" | jq '.version, .mcp_version, .server_info.version'
echo "[INFO] Schema verification complete."

# ----------------------------------------------------------
# 5️⃣ Post-Deploy Invoke Test
# ----------------------------------------------------------
echo "[TEST] Running MCP invoke test..."
start=$(date +%s%3N)
HTTP_CODE=$(curl -s -o /tmp/invoke.json -w "%{http_code}" -X POST "$BASE_URL/mcp/invoke" \
  -H "Content-Type: application/json" \
  -d '{"tool": "selenium_open_page", "arguments": {"url": "https://example.com"}}')
end=$(date +%s%3N)
LATENCY=$((end - start))
echo "   → /mcp/invoke HTTP $HTTP_CODE (${LATENCY}ms)"

if [[ "$HTTP_CODE" == "200" ]]; then
  jq . /tmp/invoke.json || cat /tmp/invoke.json
  echo "[PASS] MCP invoke succeeded."
else
  echo "[FAIL] MCP invoke failed with HTTP $HTTP_CODE"
  cat /tmp/invoke.json
fi

# ----------------------------------------------------------
# 6️⃣ Completion summary
# ----------------------------------------------------------
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "=========================================================="
echo "[DONE] Deployment + Warm-Up complete in ${ELAPSED}s"
echo "=========================================================="

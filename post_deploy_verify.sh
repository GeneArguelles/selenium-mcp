#!/usr/bin/env bash
# ==========================================================
# post_deploy_verify.sh  —  Render MCP post-deployment audit
# ----------------------------------------------------------
# Confirms live availability of:
#   1️⃣ Root manifest
#   2️⃣ Schema endpoint
#   3️⃣ Invoke tool execution
# Exits non-zero on any failure.
# ==========================================================

# ----- Configurable endpoint (change if service name differs)
BASE_URL="https://selenium-mcp.onrender.com"

# ----- Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ----- Simple fail-fast function
fail() {
  echo -e "${RED}❌ FAIL${NC} — $1"
  exit 1
}

# ----- 1️⃣ Root manifest
echo "=========================================================="
echo "1️⃣ Checking Root Manifest ($BASE_URL/)"
echo "=========================================================="
HTTP_CODE=$(curl -s -o response_root.json -w "%{http_code}" "$BASE_URL/")
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Root manifest not reachable (HTTP $HTTP_CODE)"
fi
grep -q '"type": "mcp_server"' response_root.json || fail "Missing mcp_server type in manifest"
echo -e "${GREEN}✅ PASS${NC} — Root manifest reachable and valid"
echo ""

# ----- 2️⃣ Schema endpoint
echo "=========================================================="
echo "2️⃣ Checking Schema Endpoint ($BASE_URL/mcp/schema)"
echo "=========================================================="
HTTP_CODE=$(curl -s -o response_schema.json -w "%{http_code}" "$BASE_URL/mcp/schema")
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Schema endpoint failed (HTTP $HTTP_CODE)"
fi
grep -q '"selenium_open_page"' response_schema.json || fail "selenium_open_page tool not found in schema"
echo -e "${GREEN}✅ PASS${NC} — Schema endpoint verified"
echo ""

# ----- 3️⃣ Invoke endpoint
echo "=========================================================="
echo "3️⃣ Checking Invoke Endpoint ($BASE_URL/mcp/invoke)"
echo "=========================================================="
PAYLOAD='{"tool":"selenium_open_page","arguments":{"url":"https://example.com"}}'
HTTP_CODE=$(curl -s -o response_invoke.json -X POST \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "%{http_code}" "$BASE_URL/mcp/invoke")

if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Invoke endpoint failed (HTTP $HTTP_CODE)"
fi
grep -q '"title": "Example Domain"' response_invoke.json || fail "Invoke response missing expected title"
echo -e "${GREEN}✅ PASS${NC} — Invoke endpoint functional"
echo ""

# ----- 4️⃣ Optional Render log summary (if running on Render CLI)
if command -v render &> /dev/null; then
  echo "=========================================================="
  echo "4️⃣ (Optional) Fetching latest Render logs summary..."
  echo "=========================================================="
  render logs --tail 20 || echo -e "${YELLOW}⚠️  Skipping Render logs (CLI not found)${NC}"
  echo ""
fi

echo -e "${GREEN}🎉 MCP verification succeeded — All endpoints operational.${NC}"
exit 0

#!/bin/bash
# ==========================================================
# validate_mcp.sh — MCP Post-Deploy Validator (CI-Ready)
# Exits non-zero if any endpoint check fails
# ==========================================================

BASE_URL="https://selenium-mcp.onrender.com"
FAIL=0

# === ANSI Colors ===
GREEN="\033[0;32m"
RED="\033[0;31m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"
DIVIDER="----------------------------------------------------------"

# === Helper ===
check_response() {
  local label=$1
  local url=$2
  local expect=$3
  local result
  result=$(curl -s -o /dev/null -w "%{http_code}" "$url")

  if [[ "$result" == "$expect" ]]; then
    echo -e "${GREEN}✅ PASS${RESET} — $label ($url)"
  else
    echo -e "${RED}❌ FAIL${RESET} — $label ($url) [HTTP $result]"
    FAIL=1
  fi
}

# === Start Validation ===
echo -e "${CYAN}"
echo "=========================================================="
echo " 🧩 MCP Validation Suite — Selenium MCP"
echo "=========================================================="
echo -e "${RESET}"

# === 1️⃣ Manifest Check ===
echo -e "${YELLOW}1️⃣ Root manifest check...${RESET}"
curl -s "$BASE_URL/" | jq . | head -20
check_response "Root manifest reachable" "$BASE_URL/" "200"
echo "$DIVIDER"

# === 2️⃣ Schema Check ===
echo -e "${YELLOW}2️⃣ /mcp/schema check...${RESET}"
curl -s "$BASE_URL/mcp/schema" | jq . | head -20
check_response "Schema endpoint reachable" "$BASE_URL/mcp/schema" "200"
echo "$DIVIDER"

# === 3️⃣ Tool Invocation Check ===
echo -e "${YELLOW}3️⃣ Tool invocation (/mcp/invoke)...${RESET}"
curl -s -X POST "$BASE_URL/mcp/invoke" \
  -H "Content-Type: application/json" \
  -d '{"tool":"selenium_open_page","arguments":{"url":"https://example.com"}}' | jq . | head -20
check_response "Tool invocation success" "$BASE_URL/mcp/invoke" "200"
echo "$DIVIDER"

# === Final Outcome ===
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}✅ All validations passed. MCP is production-ready.${RESET}"
else
  echo -e "${RED}❌ One or more checks failed. MCP not ready.${RESET}"
  exit 1
fi

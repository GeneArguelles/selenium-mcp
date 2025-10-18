#!/bin/bash
# ==========================================================
# validate_mcp.sh — Post-deploy MCP validation suite (CI-ready)
# Exits with code 1 if any endpoint check fails
# ==========================================================

BASE_URL="https://selenium-mcp.onrender.com"

# ANSI colors
GREEN="\033[0;32m"
RED="\033[0;31m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"

DIVIDER="----------------------------------------------------------"
FAIL=0   # Flag to track failures

# === Helper function ===
check_response() {
  local description=$1
  local url=$2
  local expect=$3
  local result
  result=$(curl -s -o /dev/null -w "%{http_code}" "$url")

  if [[ "$result" == "$expect" ]]; then
    echo -e "${GREEN}✅ PASS${RESET} — $description ($url)"
  else
    echo -e "${RED}❌ FAIL${RESET} — $description ($url) [HTTP $result]"
    FAIL=1
  fi
}

# === Fail-fast handler ===
fail_fast() {
  if [[ $FAIL -ne 0 ]]; then
    echo -e "${RED}🚨 One or more checks failed. Exiting early.${RESET}"
    exit 1
  fi
}

echo -e "${CYAN}"
echo "=========================================================="
echo " 🧩 MCP Validation Suite — Selenium MCP (CI Mode)"
echo "=========================================================="
echo -e "${RESET}"

# === 1️⃣ Root Manifest Check ===
echo -e "${YELLOW}1️⃣ Checking root manifest (/)...${RESET}"
curl -s "$BASE_URL/" | jq . | head -20
check_response "Root manifest reachable" "$BASE_URL/" "200"
fail_fast
echo "$DIVIDER"

# === 2️⃣ Schema Endpoint Check ===
echo -e "${YELLOW}2️⃣ Checking schema endpoint (/mcp/schema)...${RESET}"
curl -s "$BASE_URL/mcp/schema" | jq . | head -20
check_response "Schema endpoint reachable" "$BASE_URL/mcp/schema" "200"
fail_fast
echo "$DIVIDER"

# === 3️⃣ Invocation Test ===
echo -e "${YELLOW}3️⃣ Running sample invoke (/mcp/invoke)...${RESET}"
curl -s -X POST "$BASE_URL/mcp/invoke" \
  -H "Content-Type: application/json" \
  -d '{"tool":"selenium_open_page","arguments":{"url":"https://example.com"}}' | jq . | head -20
check_response "Invoke test completed" "$BASE_URL/mcp/invoke" "200"
fail_fast
echo "$DIVIDER"

# === Summary ===
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}✅ All validations passed.${RESET}"
  echo "Agent Builder connection ready."
else
  echo -e "${RED}❌ Validation failed.${RESET}"
  exit 1
fi

#!/bin/bash
# ==========================================================
# validate_mcp.sh — Post-deploy MCP validation suite (CI-ready)
# Exits with code 1 if any endpoint check fails
# ==========================================================

# --- 1. Define BASE URL ---
BASE_URL="https://selenium-mcp.onrender.com"

# --- 2. ANSI color codes for pretty output ---
GREEN="\033[0;32m"
RED="\033[0;31m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"

DIVIDER="----------------------------------------------------------"
FAIL=0   # Track failures across all tests

# ==========================================================
# 3️⃣ Function: check_response()
# Checks HTTP status code against expected value
# ==========================================================
check_response() {
  local description=$1             # Human-readable label
  local url=$2                     # Endpoint URL
  local expect=$3                  # Expected HTTP status
  local result

  result=$(curl -s -o /dev/null -w "%{http_code}" "$url")

  if [[ "$result" == "$expect" ]]; then
    echo -e "${GREEN}✅ PASS${RESET} — $description ($url)"
  else
    echo -e "${RED}❌ FAIL${RESET} — $description ($url) [HTTP $result]"
    FAIL=1
  fi
}

# ==========================================================
# 4️⃣ Function: fail_fast()
# Terminates script if FAIL flag is set
# ==========================================================
fail_fast() {
  if [[ $FAIL -ne 0 ]]; then
    echo -e "${RED}🚨 One or more checks failed. Exiting early.${RESET}"
    exit 1
  fi
}

# ==========================================================
# 5️⃣ Banner Header
# ==========================================================
echo -e "${CYAN}"
echo "=========================================================="
echo " 🧩 MCP Validation Suite — Selenium MCP (CI Mode)"
echo "=========================================================="
echo -e "${RESET}"

# ==========================================================
# 6️⃣ Root Manifest Check — /
# ==========================================================
echo -e "${YELLOW}1️⃣ Checking root manifest (/)...${RESET}"
curl -s "$BASE_URL/" | jq . | head -20                     # Preview first 20 lines of manifest
check_response "Root manifest reachable" "$BASE_URL/" "200"
fail_fast
echo "$DIVIDER"

# ==========================================================
# 7️⃣ Schema Check — /mcp/schema
# ==========================================================
echo -e "${YELLOW}2️⃣ Checking schema endpoint (/mcp/schema)...${RESET}"
curl -s "$BASE_URL/mcp/schema" | jq . | head -20
check_response "Schema endpoint reachable" "$BASE_URL/mcp/schema" "200"
fail_fast
echo "$DIVIDER"

# ==========================================================
# 8️⃣ Invocation Check — /mcp/invoke
# Performs POST with tool + argument
# ==========================================================
echo -e "${YELLOW}3️⃣ Running sample invoke (/mcp/invoke)...${RESET}"
curl -s -X POST "$BASE_URL/mcp/invoke" \
  -H "Content-Type: application/json" \
  -d '{"tool":"selenium_open_page","arguments":{"url":"https://example.com"}}' | jq . | head -20

check_response "Invoke test completed" "$BASE_URL/mcp/invoke" "200"
fail_fast
echo "$DIVIDER"

# ==========================================================
# 9️⃣ Summary & Exit
# ==========================================================
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}✅ All validations passed.${RESET}"
  echo "Agent Builder connection ready."
else
  echo -e "${RED}❌ Validation failed.${RESET}"
  exit 1
fi

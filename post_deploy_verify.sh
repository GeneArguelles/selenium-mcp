#!/usr/bin/env bash
BASE_URL="https://selenium-mcp.onrender.com"

echo "=========================================================="
echo "✅ Post-Deploy Verification — MCP Runtime"
echo "=========================================================="

for ENDPOINT in "/" "/health" "/mcp/schema" "/mcp/invoke" "/live"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$ENDPOINT")
  if [ "$STATUS" == "200" ]; then
    echo -e "[\033[0;32mPASS\033[0m] $ENDPOINT — $STATUS"
  else
    echo -e "[\033[0;31mFAIL\033[0m] $ENDPOINT — $STATUS"
  fi
done

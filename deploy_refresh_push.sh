#!/usr/bin/env bash
# ==========================================================
# deploy_refresh_push.sh (v2025.10.20c)
# Purpose:
#   1️⃣ Ensure all scripts are executable
#   2️⃣ Commit & push changes to Render repo
#   3️⃣ Wait for Render deployment to complete
#   4️⃣ Auto-run post_deploy_verify.sh to confirm endpoints
# ==========================================================

set -e

BASE_URL="https://selenium-mcp.onrender.com"
VERIFY_SCRIPT="./post_deploy_verify.sh"

echo "=========================================================="
echo "🚀 Render MCP Project — Commit, Push & Verify"
echo "=========================================================="

# 1️⃣ Ensure scripts are executable
chmod +x start.sh || true
chmod +x post_deploy_verify.sh || true
chmod +x force_refresh_mcp.sh || true
chmod +x diagnose_mcp_runtime.sh 2>/dev/null || true
echo "[INFO] ✅ Executable permissions refreshed."

# 2️⃣ Stage relevant files
git add server.py start.sh post_deploy_verify.sh force_refresh_mcp.sh .env 2>/dev/null

# 3️⃣ Commit with timestamp
TS=$(date +"%Y-%m-%d %H:%M:%S")
git commit -m "Render MCP: deploy sync (${TS})" || echo "[WARN] Nothing new to commit."

# 4️⃣ Push to main
echo "[INFO] 🛰️  Pushing changes to remote (origin/main)..."
git push origin main && echo "[INFO] ✅ Push successful — Render will redeploy." || { echo "[ERROR] Push failed."; exit 1; }

# 5️⃣ Wait for Render to rebuild & deploy
echo "=========================================================="
echo "⏳ Waiting for Render deployment to finish..."
echo "   (This may take 45–90 seconds depending on image size)"
echo "=========================================================="

for i in {1..18}; do  # 18 × 5s = 90s max wait
  sleep 5
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" || echo "000")
  if [ "$STATUS" == "200" ]; then
    echo "[✅] Render deployment healthy after $((i*5)) seconds."
    break
  else
    echo "[...] Waiting ($((i*5))s): health check = ${STATUS}"
  fi
  if [ "$i" -eq 18 ]; then
    echo "[❌] Render did not return healthy within timeout."
    exit 1
  fi
done

# 6️⃣ Run post-deployment verification
if [ -f "$VERIFY_SCRIPT" ]; then
  echo "=========================================================="
  echo "🔎 Running post-deployment verification..."
  echo "=========================================================="
  bash "$VERIFY_SCRIPT"
else
  echo "[WARN] post_deploy_verify.sh not found — skipping verification."
fi

echo "=========================================================="
echo "🏁 Deployment & verification sequence complete."
echo "=========================================================="

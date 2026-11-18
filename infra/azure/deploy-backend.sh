#!/usr/bin/env bash
# Creates or updates the backend Container Apps (run by .github/workflows/deploy.yml after the images
# are pushed; works in Cloud Shell too with the same variables exported).
#
#   al-ai    AI engine, internal ingress only: reachable from al-core, not from the internet
#   al-core  AL-Core REST API, public HTTPS
#
# Both scale to zero when idle, so they stay inside the Container Apps free grant
# (the first request after a pause takes a few seconds longer).
set -euo pipefail

: "${RG:?}" "${ACA_ENV:?}" "${ACR_NAME:?}" "${PULL_IDENTITY:?}" "${API_IMAGE:?}" "${AI_IMAGE:?}"
: "${INTERNAL_API_KEY:?set the INTERNAL_API_KEY secret}"
: "${FIREBASE_SERVICE_ACCOUNT_JSON:?set the FIREBASE_SERVICE_ACCOUNT_JSON secret}"
API_APP="${API_APP:-al-core}"
AI_APP="${AI_APP:-al-ai}"
WEB_APP="${WEB_APP:-al-web}"
FIRESTORE_DATABASE="${FIRESTORE_DATABASE:-default}"

# shellcheck source=infra/azure/lib.sh
source "$(dirname "$0")/lib.sh"

# CORS: AL-Web's address (al-web.<environment domain>), unless given explicitly as a JSON list
WEB_ORIGINS="${WEB_ORIGINS:-[\"https://$WEB_APP.$(aca_domain)\"]}"

# Optional secrets: Container Apps rejects empty values, so only add the ones that are set
ai_secrets=("internal-key=$INTERNAL_API_KEY")
ai_env=("INTERNAL_API_KEY=secretref:internal-key" "ENVIRONMENT=production")
[ -n "${HF_TOKEN:-}" ] && ai_secrets+=("hf-token=$HF_TOKEN") && ai_env+=("HF_TOKEN=secretref:hf-token")
[ -n "${GROQ_API_KEY:-}" ] && ai_secrets+=("groq-key=$GROQ_API_KEY") && ai_env+=("GROQ_API_KEY=secretref:groq-key")
[ -n "${GEMINI_API_KEY:-}" ] && ai_secrets+=("gemini-key=$GEMINI_API_KEY") && ai_env+=("GEMINI_API_KEY=secretref:gemini-key")

aca_deploy "$AI_APP" "$AI_IMAGE" internal 8001 0.5 1.0Gi ai_secrets ai_env
AI_URL="https://$(aca_fqdn "$AI_APP")"
echo "AI engine (internal): $AI_URL"

# compact JSON: one line, safe as a single CLI argument
SA_JSON=$(python3 -c "import json,sys; print(json.dumps(json.loads(sys.stdin.read()), separators=(',', ':')))" \
  <<<"$FIREBASE_SERVICE_ACCOUNT_JSON")
# shellcheck disable=SC2034  # both arrays are passed to aca_deploy by name
api_secrets=("internal-key=$INTERNAL_API_KEY" "firebase-sa=$SA_JSON")
# shellcheck disable=SC2034
api_env=(
  "RUN_MODE=prod"
  "FIRESTORE_PROD_DATABASE_NAME=$FIRESTORE_DATABASE"
  "FIREBASE_SERVICE_ACCOUNT_JSON=secretref:firebase-sa"
  "INTERNAL_API_KEY=secretref:internal-key"
  "AI_ENGINE_URL=$AI_URL"
  "CORS_ORIGINS=$WEB_ORIGINS"
  # behind the Container Apps proxy: rate limiting must see the caller's IP, not the proxy's
  "FORWARDED_ALLOW_IPS=*"
)
aca_deploy "$API_APP" "$API_IMAGE" external 8000 0.25 0.5Gi api_secrets api_env
API_URL="https://$(aca_fqdn "$API_APP")"
echo "AL-Core: $API_URL"

echo "Waiting for AL-Core (scaled to zero, first start can take a while)"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 20 "$API_URL/health" >/dev/null 2>&1; then
    curl -fsS --max-time 60 "$API_URL/health/dependencies" && echo && exit 0
  fi
  sleep 10
done
echo "AL-Core did not answer /health in time: az containerapp logs show -n $API_APP -g $RG --follow" >&2
exit 1

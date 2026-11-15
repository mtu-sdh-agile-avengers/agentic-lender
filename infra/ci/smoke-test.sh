#!/usr/bin/env bash
# End-to-end check of the Docker Compose stack (emulator mode), as the clients use it:
#   emulator sign-in -> ID token -> AL-Core /users/me -> Firestore profile
#   AL-Core -> AI engine: reachable, X-Internal-Key accepted, model loaded
#
# Expects `docker compose up -d --wait firebase ai api` and the seed to have run.
# Used by .github/workflows/ci.yml; works locally too (Git Bash, macOS, Linux).
set -euo pipefail

API="${API_URL:-http://localhost:8000}"
AUTH="${AUTH_EMULATOR_URL:-http://localhost:9099}"
PASSWORD="Password1"

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

echo "== AL-Core -> AI engine"
deps=$(curl -fsS "$API/health/dependencies")
echo "$deps"
[ "$(echo "$deps" | json 'd["ai_engine"]["internal_key_accepted"]')" = "True" ] || { echo "AI engine rejected the internal key"; exit 1; }
[ "$(echo "$deps" | json 'd["ai_engine"]["model_loaded"]')" = "True" ] || { echo "AI engine has no model"; exit 1; }

check_role() {
  local email=$1 expected=$2 token profile role
  token=$(curl -fsS -X POST "$AUTH/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=ci" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$PASSWORD\",\"returnSecureToken\":true}" | json 'd["idToken"]')
  profile=$(curl -fsS -H "Authorization: Bearer $token" "$API/api/v1/users/me")
  role=$(echo "$profile" | json 'd["role"]')
  echo "$email -> $role"
  [ "$role" = "$expected" ] || { echo "expected $expected"; exit 1; }
}

echo "== Sign-in chain for every demo role"
check_role borrower@demo.agenticlender.ie retail_borrower
check_role broker@demo.agenticlender.ie mortgage_broker
check_role officer@demo.agenticlender.ie underwriting_bank_officer

echo "== No token -> 401"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/users/me")
[ "$code" = "401" ] || { echo "expected 401, got $code"; exit 1; }

echo "Smoke test passed"

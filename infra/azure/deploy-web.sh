#!/usr/bin/env bash
# Creates or updates AL-Web (nginx serving the static build, see web/Dockerfile) as a public
# Container App. Run by .github/workflows/deploy.yml after the image is pushed.
set -euo pipefail

: "${RG:?}" "${ACA_ENV:?}" "${ACR_NAME:?}" "${PULL_IDENTITY:?}" "${WEB_IMAGE:?}"
WEB_APP="${WEB_APP:-al-web}"

# shellcheck source=infra/azure/lib.sh
source "$(dirname "$0")/lib.sh"

# shellcheck disable=SC2034  # passed to aca_deploy by name: no secrets, no settings
no_secrets=()
# shellcheck disable=SC2034
no_env=()
aca_deploy "$WEB_APP" "$WEB_IMAGE" external 80 0.25 0.5Gi no_secrets no_env
echo "AL-Web: https://$(aca_fqdn "$WEB_APP")"

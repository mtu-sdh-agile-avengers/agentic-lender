#!/usr/bin/env bash
# One-time Azure setup for Agentic Lender (Azure for Students subscription).
#
# Run it in Azure Cloud Shell (https://shell.azure.com, Bash) - az is already logged in there:
#   git clone https://github.com/mtu-sdh-agile-avengers/agentic-lender.git
#   cd agentic-lender && git switch feat/ALG4-XXX-integration
#   bash infra/azure/setup.sh
#
# Creates (all inside one resource group, safe to run again):
#   - Container Apps environment     al-web + al-core (public), al-ai (internal only)
#   - Container Registry             Docker images built by GitHub Actions
#   - identity "github"              GitHub Actions logs in with it (OIDC, no passwords stored)
#   - identity "pull"                the container apps pull images with it (AcrPull only)
#
# At the end it prints the values to put into GitHub (repo Settings -> Environments -> production).
# Everything fits in the Azure for Students free grants and credit; no credit card involved.
set -euo pipefail
# never fail silently: say which command stopped the script
trap 'echo "setup.sh stopped at line $LINENO: $BASH_COMMAND" >&2' ERR

GITHUB_REPO="${GITHUB_REPO:-mtu-sdh-agile-avengers/agentic-lender}"
GITHUB_ENVIRONMENT="${GITHUB_ENVIRONMENT:-production}"
# Azure for Students only allows some regions (ours: francecentral, switzerlandnorth, belgiumcentral,
# germanywestcentral, denmarkeast). If a step fails with "RequestDisallowedByAzure" /
# "RequestDisallowedByPolicy", list the allowed ones and run again with one of them:
#   az policy assignment list --disable-scope-strict-match --query "[].parameters.listOfAllowedLocations.value" -o json
#   LOCATION=germanywestcentral bash setup.sh
LOCATION="${LOCATION:-francecentral}"
RG="${RG:-agentic-lender-rg}"
ACA_ENV="${ACA_ENV:-agentic-lender-env}"
DEPLOY_IDENTITY="${DEPLOY_IDENTITY:-agentic-lender-github}"
PULL_IDENTITY="${PULL_IDENTITY:-agentic-lender-pull}"

step() { printf '\n== %s\n' "$*"; }

step "Subscription"
az account show --query "{name:name, id:id, tenant:tenantId}" -o table

step "Resource providers (first time takes a few minutes)"
for ns in Microsoft.App Microsoft.ContainerRegistry Microsoft.ManagedIdentity; do
  az provider register --namespace "$ns" --wait
done

step "Resource group $RG"
# an existing group keeps its region; resources inside may live in another region
az group show --name "$RG" -o none 2>/dev/null || az group create --name "$RG" --location "$LOCATION" -o none
RG_ID=$(az group show --name "$RG" --query id -o tsv)

step "Container Registry"
ACR=$(az acr list --resource-group "$RG" --query "[0].name" -o tsv)
if [ -z "$ACR" ]; then
  # Registry names are global: add a random suffix. Standard is in the student free offer (12 months).
  ACR="agenticlender$(printf '%05d' $((RANDOM % 100000)))"
  az acr create --name "$ACR" --resource-group "$RG" --location "$LOCATION" --sku Standard -o none
fi
ACR_ID=$(az acr show --name "$ACR" --query id -o tsv)
echo "registry: $ACR.azurecr.io"

step "Container Apps environment $ACA_ENV"
if ! az containerapp env show --name "$ACA_ENV" --resource-group "$RG" -o none 2>/dev/null; then
  # no Log Analytics workspace: it is billed per GB. Live logs still work:
  #   az containerapp logs show -n al-core -g $RG --follow
  az containerapp env create --name "$ACA_ENV" --resource-group "$RG" --location "$LOCATION" \
    --logs-destination none -o none
fi

DOMAIN=$(az containerapp env show --name "$ACA_ENV" --resource-group "$RG" --query properties.defaultDomain -o tsv)
echo "web will be:     https://al-web.$DOMAIN"
echo "AL-Core will be: https://al-core.$DOMAIN"

identity() {  # name -> creates if missing, prints principalId
  az identity show --name "$1" --resource-group "$RG" -o none 2>/dev/null \
    || az identity create --name "$1" --resource-group "$RG" --location "$LOCATION" -o none
  az identity show --name "$1" --resource-group "$RG" --query principalId -o tsv
}

grant() {  # principalId role scope (skips if already granted)
  if [ -z "$(az role assignment list --assignee "$1" --role "$2" --scope "$3" --query "[0].id" -o tsv)" ]; then
    az role assignment create --assignee-object-id "$1" --assignee-principal-type ServicePrincipal \
      --role "$2" --scope "$3" -o none
  fi
}

step "Identity for GitHub Actions ($DEPLOY_IDENTITY): Contributor on $RG only"
DEPLOY_PRINCIPAL=$(identity "$DEPLOY_IDENTITY")
grant "$DEPLOY_PRINCIPAL" Contributor "$RG_ID"
federated() {  # credential-name subject: only jobs in this repo's environment can log in
  if ! az identity federated-credential show --name "$1" --identity-name "$DEPLOY_IDENTITY" \
       --resource-group "$RG" -o none 2>/dev/null; then
    az identity federated-credential create --name "$1" --identity-name "$DEPLOY_IDENTITY" \
      --resource-group "$RG" --issuer https://token.actions.githubusercontent.com \
      --subject "$2" --audiences api://AzureADTokenExchange -o none
  fi
}
# GitHub sends one of two subject formats, depending on the organisation's OIDC settings:
#   repo:<owner>/<repo>:environment:<env>
#   repo:<owner>@<owner id>/<repo>@<repo id>:environment:<env>   (immutable IDs; ours uses this)
federated "github-$GITHUB_ENVIRONMENT" "repo:$GITHUB_REPO:environment:$GITHUB_ENVIRONMENT"
IDS=$(curl -fsS "https://api.github.com/repos/$GITHUB_REPO" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['owner']['login'], d['owner']['id'], d['name'], d['id'])")
read -r OWNER OWNER_ID REPO_NAME REPO_ID <<<"$IDS"
federated "github-$GITHUB_ENVIRONMENT-ids" \
  "repo:$OWNER@$OWNER_ID/$REPO_NAME@$REPO_ID:environment:$GITHUB_ENVIRONMENT"

step "Identity for pulling images ($PULL_IDENTITY): AcrPull only"
PULL_PRINCIPAL=$(identity "$PULL_IDENTITY")
grant "$PULL_PRINCIPAL" AcrPull "$ACR_ID"

CLIENT_ID=$(az identity show --name "$DEPLOY_IDENTITY" --resource-group "$RG" --query clientId -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

cat <<EOF

Done. In GitHub: $GITHUB_REPO -> Settings -> Environments -> New environment "$GITHUB_ENVIRONMENT".

Environment variables (not secret):
  AZURE_CLIENT_ID          $CLIENT_ID
  AZURE_TENANT_ID          $TENANT_ID
  AZURE_SUBSCRIPTION_ID    $SUBSCRIPTION_ID
  AZURE_RESOURCE_GROUP     $RG
  AZURE_CONTAINERAPPS_ENV  $ACA_ENV
  AZURE_ACR_NAME           $ACR
  AZURE_PULL_IDENTITY      $PULL_IDENTITY
  FIREBASE_WEB_API_KEY     <Firebase web app apiKey>
  FIREBASE_WEB_APP_ID      <Firebase web app appId>

Environment secrets: see docs/deploy.md (FIREBASE_SERVICE_ACCOUNT_JSON, INTERNAL_API_KEY,
GOOGLE_SERVICES_JSON, optional HF_TOKEN / GROQ_API_KEY / GEMINI_API_KEY).
Firebase Console -> Authentication -> Settings -> Authorized domains: add al-web.$DOMAIN
Then run the "Deploy (Azure)" workflow.
EOF

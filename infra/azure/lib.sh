# shellcheck shell=bash
# Shared by deploy-backend.sh and deploy-web.sh: create or update one Azure Container App.
# Needs RG, ACA_ENV, ACR_NAME, PULL_IDENTITY in the environment.

# app image ingress port cpu memory secrets-array-name env-array-name
# Apps scale to zero when idle (inside the Container Apps free grant), at most one replica.
aca_deploy() {
  local app=$1 image=$2 ingress=$3 port=$4 cpu=$5 memory=$6
  local -n _secrets=$7 _envs=$8
  local registry="$ACR_NAME.azurecr.io" pull_id
  pull_id=$(az identity show --name "$PULL_IDENTITY" --resource-group "$RG" --query id -o tsv)

  local secret_args=() env_args=()
  [ ${#_secrets[@]} -gt 0 ] && secret_args=(--secrets "${_secrets[@]}")

  if az containerapp show --name "$app" --resource-group "$RG" -o none 2>/dev/null; then
    echo "updating $app"
    [ ${#_secrets[@]} -gt 0 ] && az containerapp secret set --name "$app" --resource-group "$RG" "${secret_args[@]}" -o none
    [ ${#_envs[@]} -gt 0 ] && env_args=(--replace-env-vars "${_envs[@]}")
    az containerapp update --name "$app" --resource-group "$RG" --image "$image" \
      --cpu "$cpu" --memory "$memory" --min-replicas 0 --max-replicas 1 \
      "${env_args[@]}" -o none
  else
    echo "creating $app"
    [ ${#_envs[@]} -gt 0 ] && env_args=(--env-vars "${_envs[@]}")
    az containerapp create --name "$app" --resource-group "$RG" --environment "$ACA_ENV" \
      --image "$image" --registry-server "$registry" \
      --user-assigned "$pull_id" --registry-identity "$pull_id" \
      --ingress "$ingress" --target-port "$port" \
      --cpu "$cpu" --memory "$memory" --min-replicas 0 --max-replicas 1 \
      "${secret_args[@]}" "${env_args[@]}" -o none
  fi
}

aca_fqdn() {
  az containerapp show --name "$1" --resource-group "$RG" --query properties.configuration.ingress.fqdn -o tsv
}

# Public apps get https://<app>.<this domain>, known before the app exists
aca_domain() {
  az containerapp env show --name "$ACA_ENV" --resource-group "$RG" --query properties.defaultDomain -o tsv
}

#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sgpv}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[check] no existe archivo de entorno: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

errors=0

require_var() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    echo "[check] falta variable requerida: $name"
    errors=$((errors + 1))
  fi
}

require_not_default() {
  local name="$1"
  local bad="$2"
  local value="${!name:-}"
  if [[ "$value" == "$bad" ]]; then
    echo "[check] variable insegura por defecto en produccion: $name=$value"
    errors=$((errors + 1))
  fi
}

require_var "DJANGO_ENV"
require_var "SECRET_KEY"
require_var "ALLOWED_HOSTS"
require_var "DB_NAME"
require_var "DB_USER"
require_var "DB_PASSWORD"
require_var "DB_HOST"
require_var "DB_PORT"

require_not_default "DJANGO_ENV" "development"
require_not_default "SECRET_KEY" "changeme-dev-secret"

if [[ "${DEBUG:-1}" == "1" ]]; then
  echo "[check] DEBUG debe ser 0 en produccion"
  errors=$((errors + 1))
fi

if [[ "${CORS_ALLOW_ALL_ORIGINS:-0}" == "1" ]]; then
  echo "[check] CORS_ALLOW_ALL_ORIGINS no deberia ser 1 en produccion"
  errors=$((errors + 1))
fi

if [[ "$errors" -gt 0 ]]; then
  echo "[check] resultado: FALLA ($errors problemas)"
  exit 1
fi

echo "[check] entorno de produccion validado correctamente"

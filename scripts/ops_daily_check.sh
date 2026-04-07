#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sgpv}"
DOMAIN="${DOMAIN:-api.tudominio.com}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sgpv}"

info() {
  echo ""
  echo "==> $1"
}

warn() {
  echo "[warn] $1"
}

info "1) Estado de servicios"
sudo systemctl status sgpv-gunicorn sgpv-celery sgpv-celery-beat nginx redis-server postgresql --no-pager || true

info "2) Warnings/errores ultimas 24h"
sudo journalctl -u sgpv-gunicorn -u sgpv-celery -u sgpv-celery-beat -p warning --since "24 hours ago" --no-pager || true

info "3) Healthcheck local"
curl -fsS http://127.0.0.1/healthz/ && echo " [ok] local healthz"

info "4) Healthcheck publico TLS"
curl -fsS "https://${DOMAIN}/healthz/" && echo " [ok] public healthz (${DOMAIN})"

info "5) Vigencia certificado"
echo | openssl s_client -servername "${DOMAIN}" -connect "${DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates || warn "No se pudo leer certificado"

info "6) Renovacion certbot (dry-run)"
sudo certbot renew --dry-run || warn "certbot dry-run fallo"

info "7) Espacio en disco"
df -h

info "8) Ultimos backups"
if [[ -d "$BACKUP_DIR" ]]; then
  ls -lh "$BACKUP_DIR" | tail -n 20
else
  warn "No existe BACKUP_DIR: $BACKUP_DIR"
fi

info "9) Integridad backup SQL mas reciente"
if compgen -G "${BACKUP_DIR}/sgpv_db_*.sql.gz" > /dev/null; then
  latest_sql="$(ls -t "${BACKUP_DIR}"/sgpv_db_*.sql.gz | head -n 1)"
  gzip -t "$latest_sql" && echo "[ok] $latest_sql"
else
  warn "No hay backups SQL en ${BACKUP_DIR}"
fi

info "10) Validacion entorno produccion"
if [[ -x "${APP_DIR}/scripts/check_production_env.sh" ]]; then
  APP_DIR="$APP_DIR" "${APP_DIR}/scripts/check_production_env.sh"
else
  warn "No existe script check_production_env en ${APP_DIR}/scripts/"
fi

echo ""
echo "Checklist diario finalizado."

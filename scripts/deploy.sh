#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sgpv}"
BRANCH="${BRANCH:-main}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SYSTEMD_UNITS=("sgpv-gunicorn" "sgpv-celery" "sgpv-celery-beat")

cd "$APP_DIR"

echo "[deploy] updating code"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[deploy] ensuring virtualenv"
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo "[deploy] running checks"
"$VENV_DIR/bin/python" manage.py check
"$VENV_DIR/bin/python" manage.py migrate --noinput
"$VENV_DIR/bin/python" manage.py collectstatic --noinput || true

for unit in "${SYSTEMD_UNITS[@]}"; do
  if systemctl list-unit-files | grep -q "^${unit}.service"; then
    echo "[deploy] restarting ${unit}"
    systemctl restart "${unit}"
    systemctl status "${unit}" --no-pager --lines=3 || true
  fi
done

echo "[deploy] done"

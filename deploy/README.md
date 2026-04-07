# Deploy Tradicional (sin Docker)

Este proyecto se despliega con:
- `gunicorn` + `systemd` para la API Django
- `celery` + `systemd` para workers y tareas programadas
- `nginx` como reverse proxy
- `postgresql` y `redis` instalados en el servidor

## 1. Preparar servidor

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql redis-server
```

## 2. Copiar proyecto

```bash
sudo mkdir -p /opt/sgpv
sudo chown -R $USER:$USER /opt/sgpv
cd /opt/sgpv
git clone https://github.com/c010r/sgpv.git .
cp .env.example .env
```

Editar `.env` para producción (`DJANGO_ENV=production`, credenciales de PostgreSQL, hosts, CORS, etc.).

Checklist minimo recomendado en `.env`:
- `DJANGO_ENV=production`
- `DEBUG=0`
- `SECRET_KEY` no default
- `ALLOWED_HOSTS` definido (sin `*`)
- `CORS_ALLOW_ALL_ORIGINS=0`
- `DB_*` apuntando a PostgreSQL real
- `USE_REDIS=1` (si usaras Celery/colas en prod)
- `THROTTLE_*` ajustados al trafico esperado

Validar entorno antes de deploy:

```bash
chmod +x scripts/check_production_env.sh
APP_DIR=/opt/sgpv ./scripts/check_production_env.sh
```

## 3. Instalar servicios systemd

```bash
sudo cp deploy/systemd/sgpv-gunicorn.service /etc/systemd/system/
sudo cp deploy/systemd/sgpv-celery.service /etc/systemd/system/
sudo cp deploy/systemd/sgpv-celery-beat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sgpv-gunicorn sgpv-celery sgpv-celery-beat
```

## 4. Configurar Nginx

```bash
sudo cp deploy/nginx/sgpv.conf /etc/nginx/sites-available/sgpv
sudo ln -s /etc/nginx/sites-available/sgpv /etc/nginx/sites-enabled/sgpv
sudo nginx -t
sudo systemctl restart nginx
```

Opcional recomendado:
- TLS con Let's Encrypt (`certbot`) y redirección HTTP->HTTPS
- agregar headers de seguridad (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)

## 5. Desplegar

```bash
chmod +x scripts/deploy.sh scripts/backup.sh
APP_DIR=/opt/sgpv BRANCH=main ./scripts/deploy.sh
```

Post-deploy checklist:
- `sudo systemctl status sgpv-gunicorn sgpv-celery sgpv-celery-beat --no-pager`
- `curl -f http://127.0.0.1/healthz/` (o tu dominio)
- verificar logs `journalctl -u sgpv-gunicorn -n 100 --no-pager`
- ejecutar `pytest -q` en staging antes de prod

## 6. Backups

Programar `scripts/backup.sh` con cron (ejemplo diario 03:30):

```bash
30 3 * * * DB_NAME=sgpv DB_USER=postgres DB_PASSWORD=xxxx APP_DIR=/opt/sgpv /opt/sgpv/scripts/backup.sh >> /var/log/sgpv-backup.log 2>&1
```

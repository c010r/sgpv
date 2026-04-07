# SGPV API

API para centros nocturnos con:
- Lista de invitados (manual + CSV + check-in QR)
- Caja y ventas
- Inventario central + inventario por barra
- Reportes JSON, PDF y Excel
- Dashboard en tiempo real
- Auditoria (login/logout/fallos, caja, barra, anulaciones y ajustes)

## Base de datos
- Desarrollo: SQLite
- Produccion: PostgreSQL

## Escalabilidad
- Cache Redis (`django-redis`)
- Cola de tareas Celery con Redis
- Throttling por usuario/anonimo
- CORS configurable por variables de entorno

## Configuracion rapida
1. Crear y activar entorno virtual.
2. Instalar dependencias:
   - `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env`.
4. Ejecutar migraciones:
   - `python manage.py migrate`
5. Cargar demo opcional:
   - `python manage.py seed_demo`
6. Levantar API:
   - `python manage.py runserver`

## Usuarios demo
- `admin / admin123`
- `supervisor / super123`
- `cajero / cajero123`

## Autenticacion JWT
- Login: `POST /api/token/`
- Refresh: `POST /api/token/refresh/`
- Logout auditado: `POST /api/logout/`

## Reportes
- Dashboard: `/api/reportes/dashboard/`
- Kardex: `/api/reportes/kardex/?product_id=<id>&location_id=<id_opcional>`
- Ventas por dia: `/api/reportes/ventas-por-dia/`
- Ventas por barra: `/api/reportes/ventas-por-barra/`
- Ventas por cajero: `/api/reportes/ventas-por-cajero/`
- Cierres de caja: `/api/reportes/cierres-caja/`
- Utilidad por producto: `/api/reportes/utilidad-por-producto/`
- Utilidad por receta: `/api/reportes/utilidad-por-receta/`
- Resumen financiero: `/api/reportes/resumen-financiero/`
- Snapshots financieros (GET/POST): `/api/reportes/snapshots/`
- Alertas operativas (GET/POST): `/api/reportes/alertas/`
- Resumen alertas: `/api/reportes/alertas/resumen/`
- Resolver alerta: `POST /api/reportes/alertas/<id>/resolve/`
- Intentos de entrega por alerta: `GET /api/reportes/alertas/<id>/attempts/?channel=WEBHOOK&status=FAILED&from=YYYY-MM-DD&to=YYYY-MM-DD`
- Paginacion/orden para alertas e intentos: `?limit=50&offset=0&order_by=-id`
- Top productos: `/api/reportes/top-productos/`
- Movimientos inventario: `/api/reportes/movimientos-inventario/`

## Salud del servicio
- Healthcheck publico: `/healthz/`

El dashboard incluye:
- Resumen diario (`sales_today`, `tickets_today`)
- Sesiones abiertas (`open_bar_sessions`, `open_cash_sessions`)
- Serie horaria de ventas ultimas 24h (`hourly_sales_last_24h`)
- Alertas de stock critico por barra (`critical_stock_by_bar`)

## Exportacion
- PDF: `?export=pdf`
- Excel: `?export=xlsx`

Ejemplo:
- `/api/reportes/ventas-por-dia/?export=pdf`
- `/api/reportes/ventas-por-dia/?export=xlsx`

## Pruebas
- Ejecutar tests: `pytest -q`

## Flujos nuevos
- Cierre de caja con desglose por metodo (`CASH`, `CARD`, `TRANSFER`) y diferencia.
- Aprobacion de cierre con diferencia: `POST /api/sesiones-caja/<id>/approve_close/` (supervisor+).
- Reapertura controlada: `POST /api/sesiones-caja/<id>/reopen/` (supervisor+).
- Venta idempotente: enviar `idempotency_key` en `POST /api/ventas/create_sale/`.
- Venta con `discount_amount` y `surcharge_amount`.
- Comprobante interno: `GET /api/ventas/<id>/receipt/`.
- Invitados CSV preview: `POST /api/listas-invitados/<id>/preview_csv/`.
- Ocupacion lista invitados: `GET /api/listas-invitados/<id>/occupancy/`.
- Transferencia masiva inventario: `POST /api/inventario/movimientos/bulk_transfer/`.
- Conteo fisico/ciclico: `POST /api/inventario/conteos/start/`, `POST /api/inventario/conteos/<id>/close/`, `POST /api/inventario/conteos/<id>/apply/`.
- Import CSV con jobs persistidos: `POST /api/listas-invitados/<id>/import_csv/` y `GET /api/listas-invitados/<id>/import_jobs/`.
- Costeo configurable (`AVG`/`FIFO`) en configuracion del sistema.
- Utilidad real por venta (`cost_total`, `gross_profit`) y por item (`line_cost_total`, `line_profit`).
- Snapshot financiero diario por task (`create_daily_financial_snapshot`) o forzado por API.
- Escaneo de alertas de stock critico y diferencias de caja (`scan_and_dispatch_alerts`).
- Deduplicacion de alertas por ventana temporal configurable (`ALERT_DEDUP_WINDOW_MINUTES`).
- Entrega de alertas multi-canal (`webhook`, `email`, `slack`, `telegram`) con reintentos (`ALERT_MAX_RETRIES`) y bitacora de intentos.
- Firma HMAC opcional para webhook saliente (`ALERT_WEBHOOK_SIGNING_SECRET`) via headers de firma/timestamp.

## Permisos
- Matriz RBAC documentada en `docs/permissions_matrix.md`.
- Accesos a reportes auditados en `core_auditlog` (`action=REPORT_ACCESS`).

## Rate Limiting por Endpoint
- Venta (`POST /api/ventas/create_sale/`): `THROTTLE_SALES_CREATE_RATE`
- Lectura de reportes (`GET /api/reportes/*`): `THROTTLE_REPORTS_READ_RATE`
- Escritura en reportes (`POST /api/reportes/*`): `THROTTLE_REPORTS_WRITE_RATE`
- Escaneo de alertas (`POST /api/reportes/alertas/`): `THROTTLE_ALERTS_SCAN_RATE`

## Deploy Tradicional
- Guia completa: `deploy/README.md`
- Servicios systemd: `deploy/systemd/`
- Config Nginx: `deploy/nginx/sgpv.conf`
- Scripts: `scripts/deploy.sh`, `scripts/backup.sh` y `scripts/check_production_env.sh`
- Monitoreo diario: `scripts/ops_daily_check.sh` (usa `DOMAIN`, `APP_DIR`, `BACKUP_DIR`)

## CI
- GitHub Actions corre `manage.py check`, `migrate` y `pytest` en cada push/pull request.

## Documentacion API
- OpenAPI: `/api/schema/`
- Swagger UI: `/api/docs/`

## Frontend (Panel Web)
- Ubicacion: `frontend/`
- Archivo principal: `frontend/index.html`
- JS app: `frontend/app.js`
- Estilos: `frontend/styles.css`

Levantar frontend local (sin build):

```bash
cd frontend
python3 -m http.server 5173
```

Abrir:
- `http://127.0.0.1:5173`

Notas:
- En el panel puedes definir `API Base URL` (por defecto `http://127.0.0.1:8000`).
- Login con JWT usando tus usuarios (`admin`, `supervisor`, `cajero`).
- Modulos incluidos: dashboard, ventas, inventario, invitados, reportes y configuracion.

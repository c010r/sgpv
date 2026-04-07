# Matriz de Permisos (RBAC)

Roles:
- `SUPERADMIN`
- `SUPERVISOR`
- `CAJERO`

## Autenticacion
- `POST /api/token/`: publico
- `POST /api/token/refresh/`: publico
- `POST /api/logout/`: autenticado
- `GET /healthz/`: publico

## Usuarios
- `GET/POST/PUT/PATCH/DELETE /api/users/`: `SUPERADMIN`

## Configuracion/Barras
- `GET/POST/PUT/PATCH/DELETE /api/configuracion/`: `SUPERVISOR+`
- `GET/POST/PUT/PATCH/DELETE /api/barras/`: `SUPERVISOR+`
- `POST /api/sesiones-barra/open/`: `SUPERVISOR+`
- `POST /api/sesiones-barra/<id>/close/`: `SUPERVISOR+`

## Inventario
- `GET /api/inventario/ubicaciones/`: `CAJERO+`
- `GET /api/inventario/stocks/`: `CAJERO+`
- `GET /api/inventario/movimientos/`: `CAJERO+`
- `POST /api/inventario/movimientos/transfer/`: `SUPERVISOR+`
- `POST /api/inventario/movimientos/adjust/`: `SUPERVISOR+`
- `POST /api/inventario/movimientos/bulk_transfer/`: `SUPERVISOR+`
- `POST /api/inventario/conteos/start/`: `SUPERVISOR+`
- `POST /api/inventario/conteos/<id>/close/`: `SUPERVISOR+`
- `POST /api/inventario/conteos/<id>/apply/`: `SUPERVISOR+`

## Caja y Ventas
- `POST /api/sesiones-caja/open/`: `CAJERO+`
- `POST /api/sesiones-caja/<id>/close/`: `CAJERO+`
- `POST /api/sesiones-caja/<id>/approve_close/`: `SUPERVISOR+`
- `POST /api/sesiones-caja/<id>/reopen/`: `SUPERVISOR+`
- `POST /api/ventas/create_sale/`: `CAJERO+`
- `POST /api/ventas/<id>/cancel/`: `SUPERVISOR+`

## Invitados
- `GET /api/invitados/`: `CAJERO+`
- `POST /api/invitados/checkin/`: `CAJERO+`
- `POST/PUT/PATCH/DELETE /api/invitados/`: `SUPERVISOR+`
- `POST /api/listas-invitados/<id>/preview_csv/`: `SUPERVISOR+`
- `POST /api/listas-invitados/<id>/import_csv/`: `SUPERVISOR+`
- `GET /api/listas-invitados/<id>/import_jobs/`: `SUPERVISOR+`

## Reportes
Todos los endpoints `/api/reportes/*`: `SUPERVISOR+`
- Incluye: `/api/reportes/alertas/<id>/attempts/`

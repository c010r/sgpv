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
- Ventas por dia: `/api/reportes/ventas-por-dia/`
- Ventas por barra: `/api/reportes/ventas-por-barra/`
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

## Documentacion API
- OpenAPI: `/api/schema/`
- Swagger UI: `/api/docs/`

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import InventoryMovement, InventoryStock
from reports.excel import render_excel_report
from reports.pdf import render_pdf_report
from sales.models import CashSession, Sale, SaleItem
from settings_app.models import BarSession
from users.permissions import IsSupervisorOrAbove


def maybe_export_response(request, *, title, rows, pdf_filename, xlsx_filename):
    export_fmt = request.query_params.get("export", "").lower()
    if export_fmt == "pdf":
        return render_pdf_report(title=title, rows=rows, filename=pdf_filename)
    if export_fmt in {"xlsx", "excel"}:
        return render_excel_report(title=title, rows=rows, filename=xlsx_filename)
    return None


class SalesByDayReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            Sale.objects.filter(status=Sale.Status.COMPLETED)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total_sales=Sum("total"), total_tickets=Count("id"))
            .order_by("-day")
        )
        rows = list(queryset)
        exported = maybe_export_response(
            request,
            title="Ventas por Dia",
            rows=rows,
            pdf_filename="reporte_ventas_por_dia.pdf",
            xlsx_filename="reporte_ventas_por_dia.xlsx",
        )
        return exported or Response(rows)


class SalesByBarReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            Sale.objects.filter(status=Sale.Status.COMPLETED)
            .values("bar_session__bar__id", "bar_session__bar__name")
            .annotate(total_sales=Sum("total"), total_tickets=Count("id"))
            .order_by("-total_sales")
        )
        rows = list(queryset)
        exported = maybe_export_response(
            request,
            title="Ventas por Barra",
            rows=rows,
            pdf_filename="reporte_ventas_por_barra.pdf",
            xlsx_filename="reporte_ventas_por_barra.xlsx",
        )
        return exported or Response(rows)


class TopProductsReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            Sale.objects.filter(status=Sale.Status.COMPLETED)
            .values("items__product__id", "items__product__name")
            .annotate(quantity=Sum("items__quantity"), amount=Sum("items__line_total"))
            .order_by("-quantity")
        )
        rows = list(queryset)
        exported = maybe_export_response(
            request,
            title="Top Productos",
            rows=rows,
            pdf_filename="reporte_top_productos.pdf",
            xlsx_filename="reporte_top_productos.xlsx",
        )
        return exported or Response(rows)


class InventoryMovementsReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            InventoryMovement.objects.values("movement_type", "product__name")
            .annotate(total_qty=Sum("quantity"), count=Count("id"))
            .order_by("movement_type", "product__name")
        )
        rows = list(queryset)
        exported = maybe_export_response(
            request,
            title="Movimientos de Inventario",
            rows=rows,
            pdf_filename="reporte_movimientos_inventario.pdf",
            xlsx_filename="reporte_movimientos_inventario.xlsx",
        )
        return exported or Response(rows)


class ProfitByProductReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            SaleItem.objects.filter(sale__status=Sale.Status.COMPLETED)
            .values("product__id", "product__name")
            .annotate(
                quantity=Sum("quantity"),
                revenue=Sum("line_total"),
                cost=Sum("line_cost_total"),
                profit=Sum("line_profit"),
            )
            .order_by("-profit")
        )
        rows = []
        for row in queryset:
            revenue = row["revenue"] or 0
            profit = row["profit"] or 0
            margin = (profit / revenue * 100) if revenue else 0
            rows.append(
                {
                    "product_id": row["product__id"],
                    "product_name": row["product__name"],
                    "quantity": str(row["quantity"] or 0),
                    "revenue": str(revenue),
                    "cost": str(row["cost"] or 0),
                    "profit": str(profit),
                    "margin_pct": f"{margin:.2f}",
                }
            )
        exported = maybe_export_response(
            request,
            title="Utilidad por Producto",
            rows=rows,
            pdf_filename="reporte_utilidad_por_producto.pdf",
            xlsx_filename="reporte_utilidad_por_producto.xlsx",
        )
        return exported or Response(rows)


class ProfitByRecipeReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            SaleItem.objects.filter(sale__status=Sale.Status.COMPLETED, product__recipe__isnull=False)
            .values("product__id", "product__name", "product__recipe__name")
            .annotate(
                quantity=Sum("quantity"),
                revenue=Sum("line_total"),
                cost=Sum("line_cost_total"),
                profit=Sum("line_profit"),
            )
            .order_by("-profit")
        )
        rows = []
        for row in queryset:
            revenue = row["revenue"] or 0
            profit = row["profit"] or 0
            margin = (profit / revenue * 100) if revenue else 0
            rows.append(
                {
                    "product_id": row["product__id"],
                    "product_name": row["product__name"],
                    "recipe_name": row["product__recipe__name"],
                    "quantity": str(row["quantity"] or 0),
                    "revenue": str(revenue),
                    "cost": str(row["cost"] or 0),
                    "profit": str(profit),
                    "margin_pct": f"{margin:.2f}",
                }
            )
        exported = maybe_export_response(
            request,
            title="Utilidad por Receta",
            rows=rows,
            pdf_filename="reporte_utilidad_por_receta.pdf",
            xlsx_filename="reporte_utilidad_por_receta.xlsx",
        )
        return exported or Response(rows)


class FinancialSummaryReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        qs = Sale.objects.filter(status=Sale.Status.COMPLETED)
        agg = qs.aggregate(
            revenue=Sum("total"),
            subtotal=Sum("subtotal"),
            discounts=Sum("discount_amount"),
            surcharges=Sum("surcharge_amount"),
            cost=Sum("cost_total"),
            profit=Sum("gross_profit"),
            tickets=Count("id"),
        )
        revenue = agg["revenue"] or 0
        profit = agg["profit"] or 0
        margin = (profit / revenue * 100) if revenue else 0
        rows = [
            {
                "tickets": agg["tickets"] or 0,
                "subtotal": str(agg["subtotal"] or 0),
                "discounts": str(agg["discounts"] or 0),
                "surcharges": str(agg["surcharges"] or 0),
                "revenue": str(revenue),
                "cost": str(agg["cost"] or 0),
                "profit": str(profit),
                "margin_pct": f"{margin:.2f}",
            }
        ]
        exported = maybe_export_response(
            request,
            title="Resumen Financiero",
            rows=rows,
            pdf_filename="reporte_resumen_financiero.pdf",
            xlsx_filename="reporte_resumen_financiero.xlsx",
        )
        return exported or Response(rows[0])


class SalesByCashierReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            Sale.objects.filter(status=Sale.Status.COMPLETED)
            .values("created_by__id", "created_by__username")
            .annotate(total_sales=Sum("total"), total_tickets=Count("id"))
            .order_by("-total_sales")
        )
        rows = list(queryset)
        exported = maybe_export_response(
            request,
            title="Ventas por Cajero",
            rows=rows,
            pdf_filename="reporte_ventas_por_cajero.pdf",
            xlsx_filename="reporte_ventas_por_cajero.xlsx",
        )
        return exported or Response(rows)


class CashSessionCloseReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        queryset = (
            CashSession.objects.select_related("register", "opened_by", "closed_by", "approved_by")
            .all()
            .order_by("-id")
        )
        rows = []
        for session in queryset:
            rows.append(
                {
                    "id": session.id,
                    "register": session.register.name,
                    "opened_by": session.opened_by.username,
                    "closed_by": session.closed_by.username if session.closed_by else None,
                    "close_status": session.close_status,
                    "expected_amount": str(session.expected_amount),
                    "closing_amount": str(session.closing_amount or 0),
                    "difference_amount": str(session.difference_amount),
                    "approved_by": session.approved_by.username if session.approved_by else None,
                    "opened_at": session.opened_at.isoformat() if session.opened_at else None,
                    "closed_at": session.closed_at.isoformat() if session.closed_at else None,
                }
            )
        exported = maybe_export_response(
            request,
            title="Cierres de Caja",
            rows=rows,
            pdf_filename="reporte_cierres_caja.pdf",
            xlsx_filename="reporte_cierres_caja.xlsx",
        )
        return exported or Response(rows)


class DashboardReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        today = timezone.localdate()
        low_stock_threshold = request.query_params.get("low_stock_threshold", "10")
        try:
            threshold = float(low_stock_threshold)
        except ValueError:
            threshold = 10.0

        now = timezone.localtime(timezone.now())
        start_hour = (now - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0)

        sales_today = (
            Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__date=today).aggregate(total=Sum("total"))["total"]
            or 0
        )
        tickets_today = Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__date=today).count()
        open_bar_sessions = BarSession.objects.filter(is_open=True).count()
        open_cash_sessions = CashSession.objects.filter(is_open=True).count()

        low_stock = list(
            InventoryStock.objects.filter(quantity__lte=threshold)
            .values("location__name", "product__name", "quantity")
            .order_by("quantity")[:30]
        )

        hourly_qs = (
            Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__gte=start_hour)
            .annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(total_sales=Sum("total"), total_tickets=Count("id"))
            .order_by("hour")
        )
        hourly_map = {
            timezone.localtime(item["hour"]).strftime("%Y-%m-%d %H:00"): {
                "sales": str(item["total_sales"] or 0),
                "tickets": item["total_tickets"],
            }
            for item in hourly_qs
        }
        hourly_sales_last_24h = []
        cursor = start_hour
        for _ in range(24):
            label = cursor.strftime("%Y-%m-%d %H:00")
            values = hourly_map.get(label, {"sales": "0", "tickets": 0})
            hourly_sales_last_24h.append(
                {
                    "hour": label,
                    "sales": values["sales"],
                    "tickets": values["tickets"],
                }
            )
            cursor += timedelta(hours=1)

        critical_stock_raw = list(
            InventoryStock.objects.filter(quantity__lte=threshold, location__location_type="BAR")
            .values("location__id", "location__name", "location__bar__id", "location__bar__name", "product__name", "quantity")
            .order_by("location__name", "quantity")
        )
        grouped = {}
        for item in critical_stock_raw:
            key = item["location__id"]
            if key not in grouped:
                grouped[key] = {
                    "location_id": item["location__id"],
                    "location_name": item["location__name"],
                    "bar_id": item["location__bar__id"],
                    "bar_name": item["location__bar__name"],
                    "items_count": 0,
                    "items": [],
                }
            grouped[key]["items_count"] += 1
            grouped[key]["items"].append(
                {
                    "product_name": item["product__name"],
                    "quantity": str(item["quantity"]),
                }
            )

        payload = {
            "date": str(today),
            "sales_today": str(sales_today),
            "tickets_today": tickets_today,
            "open_bar_sessions": open_bar_sessions,
            "open_cash_sessions": open_cash_sessions,
            "low_stock_threshold": threshold,
            "low_stock_items": low_stock,
            "hourly_sales_last_24h": hourly_sales_last_24h,
            "critical_stock_by_bar": list(grouped.values()),
        }
        return Response(payload)


class KardexReportView(APIView):
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        product_id = request.query_params.get("product_id")
        location_id = request.query_params.get("location_id")
        if not product_id:
            return Response({"detail": "product_id es requerido"}, status=400)

        queryset = InventoryMovement.objects.filter(product_id=product_id).select_related("source", "destination", "created_by")
        if location_id:
            queryset = queryset.filter(source_id=location_id) | queryset.filter(destination_id=location_id)
        queryset = queryset.order_by("created_at", "id")

        running_delta = 0
        rows = []
        for move in queryset:
            incoming = move.destination_id is not None and (not location_id or str(move.destination_id) == str(location_id))
            outgoing = move.source_id is not None and (not location_id or str(move.source_id) == str(location_id))
            delta = 0
            if incoming and not outgoing:
                delta = float(move.quantity)
            elif outgoing and not incoming:
                delta = -float(move.quantity)
            running_delta += delta
            rows.append(
                {
                    "id": move.id,
                    "created_at": move.created_at.isoformat(),
                    "movement_type": move.movement_type,
                    "quantity": str(move.quantity),
                    "delta": str(delta),
                    "running_delta": str(running_delta),
                    "source": move.source.name if move.source else None,
                    "destination": move.destination.name if move.destination else None,
                    "reason": move.reason,
                    "created_by": move.created_by.username,
                }
            )

        exported = maybe_export_response(
            request,
            title="Kardex",
            rows=rows,
            pdf_filename="kardex.pdf",
            xlsx_filename="kardex.xlsx",
        )
        return exported or Response(rows)

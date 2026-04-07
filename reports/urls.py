from django.urls import path

from reports.views import (
    CashSessionCloseReportView,
    DashboardReportView,
    FinancialSummaryReportView,
    InventoryMovementsReportView,
    KardexReportView,
    ProfitByProductReportView,
    ProfitByRecipeReportView,
    SalesByCashierReportView,
    SalesByBarReportView,
    SalesByDayReportView,
    TopProductsReportView,
)

urlpatterns = [
    path("reportes/dashboard/", DashboardReportView.as_view(), name="reporte-dashboard"),
    path("reportes/kardex/", KardexReportView.as_view(), name="reporte-kardex"),
    path("reportes/ventas-por-cajero/", SalesByCashierReportView.as_view(), name="reporte-ventas-por-cajero"),
    path("reportes/cierres-caja/", CashSessionCloseReportView.as_view(), name="reporte-cierres-caja"),
    path("reportes/utilidad-por-producto/", ProfitByProductReportView.as_view(), name="reporte-utilidad-producto"),
    path("reportes/utilidad-por-receta/", ProfitByRecipeReportView.as_view(), name="reporte-utilidad-receta"),
    path("reportes/resumen-financiero/", FinancialSummaryReportView.as_view(), name="reporte-resumen-financiero"),
    path("reportes/ventas-por-dia/", SalesByDayReportView.as_view(), name="reporte-ventas-por-dia"),
    path("reportes/ventas-por-barra/", SalesByBarReportView.as_view(), name="reporte-ventas-por-barra"),
    path("reportes/top-productos/", TopProductsReportView.as_view(), name="reporte-top-productos"),
    path("reportes/movimientos-inventario/", InventoryMovementsReportView.as_view(), name="reporte-movimientos"),
]

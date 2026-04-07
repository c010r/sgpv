from rest_framework.routers import DefaultRouter

from sales.views import CashRegisterViewSet, CashSessionViewSet, SaleViewSet

router = DefaultRouter()
router.register("cajas", CashRegisterViewSet, basename="cajas")
router.register("sesiones-caja", CashSessionViewSet, basename="sesiones-caja")
router.register("ventas", SaleViewSet, basename="ventas")

urlpatterns = router.urls

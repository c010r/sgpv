from rest_framework.routers import DefaultRouter

from settings_app.views import BarSessionViewSet, BarViewSet, SystemConfigurationViewSet

router = DefaultRouter()
router.register("configuracion", SystemConfigurationViewSet, basename="configuracion")
router.register("barras", BarViewSet, basename="barras")
router.register("sesiones-barra", BarSessionViewSet, basename="sesiones-barra")

urlpatterns = router.urls

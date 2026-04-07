from rest_framework.routers import DefaultRouter

from inventory.views import (
    InventoryLocationViewSet,
    InventoryMovementViewSet,
    InventorySetupViewSet,
    InventoryStockViewSet,
    ProductViewSet,
    RecipeViewSet,
    StockCountViewSet,
)

router = DefaultRouter()
router.register("productos", ProductViewSet, basename="productos")
router.register("recetas", RecipeViewSet, basename="recetas")
router.register("inventario/ubicaciones", InventoryLocationViewSet, basename="inventario-ubicaciones")
router.register("inventario/stocks", InventoryStockViewSet, basename="inventario-stocks")
router.register("inventario/movimientos", InventoryMovementViewSet, basename="inventario-movimientos")
router.register("inventario/setup", InventorySetupViewSet, basename="inventario-setup")
router.register("inventario/conteos", StockCountViewSet, basename="inventario-conteos")

urlpatterns = router.urls

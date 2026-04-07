from django.contrib import admin

from inventory.models import (
    InventoryBatch,
    InventoryLocation,
    InventoryMovement,
    InventoryStock,
    Product,
    Recipe,
    RecipeItem,
    StockCountItem,
    StockCountSession,
)

admin.site.register(Product)
admin.site.register(InventoryLocation)
admin.site.register(InventoryStock)
admin.site.register(InventoryBatch)
admin.site.register(InventoryMovement)
admin.site.register(Recipe)
admin.site.register(RecipeItem)
admin.site.register(StockCountSession)
admin.site.register(StockCountItem)

from django.contrib import admin

from inventory.models import InventoryLocation, InventoryMovement, InventoryStock, Product, Recipe, RecipeItem

admin.site.register(Product)
admin.site.register(InventoryLocation)
admin.site.register(InventoryStock)
admin.site.register(InventoryMovement)
admin.site.register(Recipe)
admin.site.register(RecipeItem)

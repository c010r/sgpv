from decimal import Decimal

from django.db import models

from core.models import TimeStampedModel


class Product(TimeStampedModel):
    class Unit(models.TextChoices):
        ML = "ML", "Mililitros"
        UNIT = "UNIT", "Unidad"

    name = models.CharField(max_length=140, unique=True)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.choices)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class InventoryLocation(TimeStampedModel):
    class LocationType(models.TextChoices):
        CENTRAL = "CENTRAL", "Central"
        BAR = "BAR", "Barra"

    name = models.CharField(max_length=120, unique=True)
    location_type = models.CharField(max_length=10, choices=LocationType.choices)
    bar = models.OneToOneField(
        "settings_app.Bar", null=True, blank=True, on_delete=models.CASCADE, related_name="inventory_location"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location_type"], condition=models.Q(location_type="CENTRAL"), name="single_central_inventory"
            )
        ]

    def __str__(self):
        return self.name


class InventoryStock(TimeStampedModel):
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name="stocks")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stocks")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))

    class Meta:
        constraints = [models.UniqueConstraint(fields=["location", "product"], name="unique_stock_per_location_product")]

    def __str__(self):
        return f"{self.location} - {self.product}: {self.quantity}"


class Recipe(TimeStampedModel):
    name = models.CharField(max_length=140, unique=True)
    sale_product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="recipe")

    def __str__(self):
        return self.name


class RecipeItem(TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="ingredient_in_recipes")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_recipe_ingredient")]


class InventoryMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        TRANSFER = "TRANSFER", "Transferencia"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"
        SALE = "SALE", "Venta"

    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    source = models.ForeignKey(
        InventoryLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="outgoing_movements"
    )
    destination = models.ForeignKey(
        InventoryLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_movements"
    )
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="inventory_movements")

    def __str__(self):
        return f"{self.movement_type} {self.product} {self.quantity}"

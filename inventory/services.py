from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from core.models import AuditLog
from inventory.models import InventoryLocation, InventoryMovement, InventoryStock, Product, Recipe
from settings_app.models import Bar


@transaction.atomic
def ensure_central_inventory():
    return InventoryLocation.objects.get_or_create(
        location_type=InventoryLocation.LocationType.CENTRAL,
        defaults={"name": "Inventario Central"},
    )


@transaction.atomic
def ensure_bar_inventory(bar: Bar):
    location, _ = InventoryLocation.objects.get_or_create(
        bar=bar,
        defaults={"name": f"Barra {bar.name}", "location_type": InventoryLocation.LocationType.BAR},
    )
    if location.location_type != InventoryLocation.LocationType.BAR:
        location.location_type = InventoryLocation.LocationType.BAR
        location.save(update_fields=["location_type", "updated_at"])

    for product in Product.objects.filter(is_active=True):
        InventoryStock.objects.get_or_create(location=location, product=product)
    return location


@transaction.atomic
def transfer_stock(*, source: InventoryLocation, destination: InventoryLocation, product: Product, quantity: Decimal, user, reason=""):
    if quantity <= 0:
        raise ValidationError("La cantidad a transferir debe ser mayor a cero")

    source_stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=source, product=product)
    destination_stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=destination, product=product)

    if source_stock.quantity < quantity:
        raise ValidationError(f"Stock insuficiente de {product.name} en {source.name}")

    source_stock.quantity = F("quantity") - quantity
    source_stock.save(update_fields=["quantity", "updated_at"])

    destination_stock.quantity = F("quantity") + quantity
    destination_stock.save(update_fields=["quantity", "updated_at"])

    InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.TRANSFER,
        product=product,
        quantity=quantity,
        source=source,
        destination=destination,
        reason=reason,
        created_by=user,
    )


@transaction.atomic
def adjust_stock(*, location: InventoryLocation, product: Product, quantity_delta: Decimal, user, reason=""):
    if quantity_delta == 0:
        raise ValidationError("El ajuste no puede ser cero")

    stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=location, product=product)
    new_qty = stock.quantity + quantity_delta
    if new_qty < 0:
        raise ValidationError("El ajuste deja inventario en negativo")

    stock.quantity = new_qty
    stock.save(update_fields=["quantity", "updated_at"])

    InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        product=product,
        quantity=abs(quantity_delta),
        source=location if quantity_delta < 0 else None,
        destination=location if quantity_delta > 0 else None,
        reason=reason,
        created_by=user,
    )

    AuditLog.objects.create(
        action="INVENTORY_ADJUSTMENT",
        model_name="InventoryStock",
        object_id=str(stock.id),
        actor=user,
        metadata={"location": location.id, "product": product.id, "quantity_delta": str(quantity_delta), "reason": reason},
    )


@transaction.atomic
def consume_sale_inventory(*, bar_location: InventoryLocation, product: Product, quantity: Decimal, user):
    if quantity <= 0:
        raise ValidationError("Cantidad invalida")

    if hasattr(product, "recipe"):
        recipe: Recipe = product.recipe
        for item in recipe.items.select_related("ingredient"):
            ingredient_qty = item.quantity * quantity
            ingredient_stock, _ = InventoryStock.objects.select_for_update().get_or_create(
                location=bar_location, product=item.ingredient
            )
            if ingredient_stock.quantity < ingredient_qty:
                raise ValidationError(f"Stock insuficiente de ingrediente {item.ingredient.name}")
            ingredient_stock.quantity = F("quantity") - ingredient_qty
            ingredient_stock.save(update_fields=["quantity", "updated_at"])
            InventoryMovement.objects.create(
                movement_type=InventoryMovement.MovementType.SALE,
                product=item.ingredient,
                quantity=ingredient_qty,
                source=bar_location,
                reason=f"Consumo por venta de {product.name}",
                created_by=user,
            )
        return

    stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=bar_location, product=product)
    if stock.quantity < quantity:
        raise ValidationError(f"Stock insuficiente de {product.name}")

    stock.quantity = F("quantity") - quantity
    stock.save(update_fields=["quantity", "updated_at"])

    InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.SALE,
        product=product,
        quantity=quantity,
        source=bar_location,
        reason="Consumo por venta",
        created_by=user,
    )


@transaction.atomic
def restore_sale_inventory(*, bar_location: InventoryLocation, product: Product, quantity: Decimal, user, reason="Reversion por anulacion"):
    if quantity <= 0:
        raise ValidationError("Cantidad invalida")

    if hasattr(product, "recipe"):
        recipe: Recipe = product.recipe
        for item in recipe.items.select_related("ingredient"):
            ingredient_qty = item.quantity * quantity
            ingredient_stock, _ = InventoryStock.objects.select_for_update().get_or_create(
                location=bar_location, product=item.ingredient
            )
            ingredient_stock.quantity = F("quantity") + ingredient_qty
            ingredient_stock.save(update_fields=["quantity", "updated_at"])
            InventoryMovement.objects.create(
                movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                product=item.ingredient,
                quantity=ingredient_qty,
                destination=bar_location,
                reason=f"{reason}: {product.name}",
                created_by=user,
            )
        return

    stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=bar_location, product=product)
    stock.quantity = F("quantity") + quantity
    stock.save(update_fields=["quantity", "updated_at"])

    InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        product=product,
        quantity=quantity,
        destination=bar_location,
        reason=f"{reason}: {product.name}",
        created_by=user,
    )

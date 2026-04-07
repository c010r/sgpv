from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from inventory.models import (
    InventoryBatch,
    InventoryLocation,
    InventoryMovement,
    InventoryStock,
    Product,
    Recipe,
    StockCountItem,
    StockCountSession,
)
from settings_app.models import Bar, SystemConfiguration


def _costing_method():
    conf = SystemConfiguration.objects.order_by("id").first()
    return conf.costing_method if conf else SystemConfiguration.CostingMethod.AVG


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

    source_stock.quantity -= quantity
    source_stock.save(update_fields=["quantity", "updated_at"])

    destination_stock.quantity += quantity
    destination_stock.save(update_fields=["quantity", "updated_at"])

    movement = InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.TRANSFER,
        product=product,
        quantity=quantity,
        source=source,
        destination=destination,
        reason=reason,
        created_by=user,
    )

    # FIFO layers are tracked at destination. For now we preserve product cost.
    InventoryBatch.objects.create(
        location=destination,
        product=product,
        unit_cost=product.cost_price,
        initial_quantity=quantity,
        remaining_quantity=quantity,
        source_movement=movement,
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

    movement = InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        product=product,
        quantity=abs(quantity_delta),
        source=location if quantity_delta < 0 else None,
        destination=location if quantity_delta > 0 else None,
        reason=reason,
        created_by=user,
    )

    if quantity_delta > 0:
        InventoryBatch.objects.create(
            location=location,
            product=product,
            unit_cost=product.cost_price,
            initial_quantity=quantity_delta,
            remaining_quantity=quantity_delta,
            source_movement=movement,
        )

    AuditLog.objects.create(
        action="INVENTORY_ADJUSTMENT",
        model_name="InventoryStock",
        object_id=str(stock.id),
        actor=user,
        metadata={"location": location.id, "product": product.id, "quantity_delta": str(quantity_delta), "reason": reason},
    )


def _consume_avg_cost(product: Product, quantity: Decimal):
    return product.cost_price, (product.cost_price * quantity)


def _consume_fifo_cost(*, location: InventoryLocation, product: Product, quantity: Decimal):
    remaining = quantity
    total_cost = Decimal("0")
    batches = InventoryBatch.objects.select_for_update().filter(
        location=location,
        product=product,
        remaining_quantity__gt=0,
    ).order_by("created_at", "id")

    for batch in batches:
        if remaining <= 0:
            break
        used = min(batch.remaining_quantity, remaining)
        batch.remaining_quantity -= used
        batch.save(update_fields=["remaining_quantity", "updated_at"])
        total_cost += used * batch.unit_cost
        remaining -= used

    if remaining > 0:
        raise ValidationError(f"No hay capas FIFO suficientes para {product.name}")

    unit_cost = (total_cost / quantity) if quantity > 0 else Decimal("0")
    return unit_cost, total_cost


@transaction.atomic
def consume_sale_inventory(*, bar_location: InventoryLocation, product: Product, quantity: Decimal, user):
    if quantity <= 0:
        raise ValidationError("Cantidad invalida")

    method = _costing_method()

    if hasattr(product, "recipe"):
        recipe: Recipe = product.recipe
        total_cost = Decimal("0")

        for item in recipe.items.select_related("ingredient"):
            ingredient_qty = item.quantity * quantity
            ingredient_stock, _ = InventoryStock.objects.select_for_update().get_or_create(
                location=bar_location, product=item.ingredient
            )
            if ingredient_stock.quantity < ingredient_qty:
                raise ValidationError(f"Stock insuficiente de ingrediente {item.ingredient.name}")

            ingredient_stock.quantity -= ingredient_qty
            ingredient_stock.save(update_fields=["quantity", "updated_at"])

            if method == SystemConfiguration.CostingMethod.FIFO:
                _, line_cost = _consume_fifo_cost(
                    location=bar_location,
                    product=item.ingredient,
                    quantity=ingredient_qty,
                )
            else:
                _, line_cost = _consume_avg_cost(item.ingredient, ingredient_qty)

            total_cost += line_cost

            InventoryMovement.objects.create(
                movement_type=InventoryMovement.MovementType.SALE,
                product=item.ingredient,
                quantity=ingredient_qty,
                source=bar_location,
                reason=f"Consumo por venta de {product.name}",
                created_by=user,
            )

        recipe_unit_cost = (total_cost / quantity) if quantity > 0 else Decimal("0")
        return recipe_unit_cost, total_cost

    stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=bar_location, product=product)
    if stock.quantity < quantity:
        raise ValidationError(f"Stock insuficiente de {product.name}")

    stock.quantity -= quantity
    stock.save(update_fields=["quantity", "updated_at"])

    if method == SystemConfiguration.CostingMethod.FIFO:
        unit_cost, total_cost = _consume_fifo_cost(location=bar_location, product=product, quantity=quantity)
    else:
        unit_cost, total_cost = _consume_avg_cost(product, quantity)

    InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.SALE,
        product=product,
        quantity=quantity,
        source=bar_location,
        reason="Consumo por venta",
        created_by=user,
    )
    return unit_cost, total_cost


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
            ingredient_stock.quantity += ingredient_qty
            ingredient_stock.save(update_fields=["quantity", "updated_at"])
            movement = InventoryMovement.objects.create(
                movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                product=item.ingredient,
                quantity=ingredient_qty,
                destination=bar_location,
                reason=f"{reason}: {product.name}",
                created_by=user,
            )
            InventoryBatch.objects.create(
                location=bar_location,
                product=item.ingredient,
                unit_cost=item.ingredient.cost_price,
                initial_quantity=ingredient_qty,
                remaining_quantity=ingredient_qty,
                source_movement=movement,
            )
        return

    stock, _ = InventoryStock.objects.select_for_update().get_or_create(location=bar_location, product=product)
    stock.quantity += quantity
    stock.save(update_fields=["quantity", "updated_at"])

    movement = InventoryMovement.objects.create(
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        product=product,
        quantity=quantity,
        destination=bar_location,
        reason=f"{reason}: {product.name}",
        created_by=user,
    )
    InventoryBatch.objects.create(
        location=bar_location,
        product=product,
        unit_cost=product.cost_price,
        initial_quantity=quantity,
        remaining_quantity=quantity,
        source_movement=movement,
    )


@transaction.atomic
def start_stock_count(*, location: InventoryLocation, user, notes=""):
    if StockCountSession.objects.filter(location=location, status=StockCountSession.Status.OPEN).exists():
        raise ValidationError("Ya existe un conteo abierto para esta ubicacion")

    session = StockCountSession.objects.create(location=location, created_by=user, notes=notes)
    stocks = InventoryStock.objects.filter(location=location).select_related("product")
    StockCountItem.objects.bulk_create(
        [
            StockCountItem(
                session=session,
                product=stock.product,
                expected_quantity=stock.quantity,
            )
            for stock in stocks
        ]
    )
    return session


@transaction.atomic
def close_stock_count(*, session: StockCountSession, counted_map: dict, user):
    if session.status != StockCountSession.Status.OPEN:
        raise ValidationError("El conteo no esta abierto")

    for item in session.items.select_related("product").all():
        counted = counted_map.get(str(item.product_id))
        if counted is None:
            counted = counted_map.get(item.product_id)
        if counted is None:
            continue
        counted_val = Decimal(str(counted))
        item.counted_quantity = counted_val
        item.difference_quantity = counted_val - item.expected_quantity
        item.save(update_fields=["counted_quantity", "difference_quantity", "updated_at"])

    session.status = StockCountSession.Status.CLOSED
    session.closed_by = user
    session.closed_at = timezone.now()
    session.save(update_fields=["status", "closed_by", "closed_at", "updated_at"])
    return session


@transaction.atomic
def apply_stock_count(*, session: StockCountSession, user):
    if session.status != StockCountSession.Status.CLOSED:
        raise ValidationError("El conteo debe estar cerrado para aplicar")

    for item in session.items.select_related("product").all():
        if not item.counted_quantity:
            continue
        if item.difference_quantity == 0:
            continue
        adjust_stock(
            location=session.location,
            product=item.product,
            quantity_delta=item.difference_quantity,
            user=user,
            reason=f"Ajuste por conteo #{session.id}",
        )

    session.status = StockCountSession.Status.APPLIED
    session.applied_by = user
    session.applied_at = timezone.now()
    session.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    return session

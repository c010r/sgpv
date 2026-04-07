from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from inventory.models import InventoryLocation
from inventory.services import consume_sale_inventory, restore_sale_inventory
from sales.models import CashSession, Sale, SaleItem, SalePayment


@transaction.atomic
def open_cash_session(*, register, opening_amount: Decimal, user):
    session = CashSession.objects.create(register=register, opened_by=user, opening_amount=opening_amount)
    AuditLog.objects.create(
        action="OPEN_CASH",
        model_name="CashSession",
        object_id=str(session.id),
        actor=user,
        metadata={"register_id": register.id, "opening_amount": str(opening_amount)},
    )
    return session


@transaction.atomic
def close_cash_session(*, session: CashSession, closing_amount: Decimal, user):
    if not session.is_open:
        raise ValidationError("La caja ya esta cerrada")

    session.is_open = False
    session.closed_at = timezone.now()
    session.closed_by = user
    session.closing_amount = closing_amount
    session.save(update_fields=["is_open", "closed_at", "closed_by", "closing_amount", "updated_at"])

    AuditLog.objects.create(
        action="CLOSE_CASH",
        model_name="CashSession",
        object_id=str(session.id),
        actor=user,
        metadata={"closing_amount": str(closing_amount)},
    )
    return session


@transaction.atomic
def create_sale(*, bar_session, cash_session, items, payments, user):
    if not bar_session.is_open:
        raise ValidationError("La barra esta cerrada")
    if not cash_session.is_open:
        raise ValidationError("La caja esta cerrada")

    bar_location = InventoryLocation.objects.filter(bar=bar_session.bar).first()
    if not bar_location:
        raise ValidationError("La barra no tiene inventario configurado")

    sale = Sale.objects.create(bar_session=bar_session, cash_session=cash_session, created_by=user)

    total = Decimal("0")
    for entry in items:
        product = entry["product"]
        quantity = entry["quantity"]
        unit_price = entry.get("unit_price") or product.sale_price
        line_total = unit_price * quantity

        consume_sale_inventory(bar_location=bar_location, product=product, quantity=quantity, user=user)

        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        total += line_total

    paid_total = Decimal("0")
    for payment in payments:
        SalePayment.objects.create(sale=sale, method=payment["method"], amount=payment["amount"])
        paid_total += payment["amount"]

    if paid_total != total:
        raise ValidationError("El total de pagos no coincide con el total de la venta")

    sale.total = total
    sale.save(update_fields=["total", "updated_at"])

    cash_session.expected_amount += total
    cash_session.save(update_fields=["expected_amount", "updated_at"])

    return sale


@transaction.atomic
def cancel_sale(*, sale: Sale, reason: str, user):
    if sale.status == Sale.Status.CANCELED:
        raise ValidationError("La venta ya esta cancelada")

    if user.role not in {"SUPERADMIN", "SUPERVISOR"}:
        raise ValidationError("Solo supervisor o superadmin pueden anular ventas")

    bar_location = InventoryLocation.objects.filter(bar=sale.bar_session.bar).first()
    if not bar_location:
        raise ValidationError("La barra de la venta no tiene inventario configurado")

    for item in sale.items.select_related("product").all():
        restore_sale_inventory(
            bar_location=bar_location,
            product=item.product,
            quantity=item.quantity,
            user=user,
            reason="Reversion por anulacion de venta",
        )

    sale.status = Sale.Status.CANCELED
    sale.cancel_reason = reason
    sale.canceled_by = user
    sale.save(update_fields=["status", "cancel_reason", "canceled_by", "updated_at"])

    sale.cash_session.expected_amount -= sale.total
    sale.cash_session.save(update_fields=["expected_amount", "updated_at"])

    AuditLog.objects.create(
        action="CANCEL_SALE",
        model_name="Sale",
        object_id=str(sale.id),
        actor=user,
        metadata={"reason": reason, "total": str(sale.total)},
    )

    return sale

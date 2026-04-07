from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
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
def create_sale(*, bar_session, cash_session, items, payments, user, discount_amount=Decimal("0"), surcharge_amount=Decimal("0"), idempotency_key=None):
    if idempotency_key:
        existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

    if not bar_session.is_open:
        raise ValidationError("La barra esta cerrada")
    if not cash_session.is_open:
        raise ValidationError("La caja esta cerrada")

    bar_location = InventoryLocation.objects.filter(bar=bar_session.bar).first()
    if not bar_location:
        raise ValidationError("La barra no tiene inventario configurado")

    sale = Sale.objects.create(
        bar_session=bar_session,
        cash_session=cash_session,
        created_by=user,
        idempotency_key=idempotency_key,
        discount_amount=discount_amount,
        surcharge_amount=surcharge_amount,
    )

    subtotal = Decimal("0")
    cost_total = Decimal("0")
    for entry in items:
        product = entry["product"]
        quantity = entry["quantity"]
        unit_price = entry.get("unit_price") or product.sale_price
        line_total = unit_price * quantity

        unit_cost, line_cost_total = consume_sale_inventory(bar_location=bar_location, product=product, quantity=quantity, user=user)
        line_profit = line_total - line_cost_total

        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            line_cost_total=line_cost_total,
            line_profit=line_profit,
            line_total=line_total,
        )
        subtotal += line_total
        cost_total += line_cost_total

    total = subtotal - discount_amount + surcharge_amount
    if total < 0:
        raise ValidationError("El total no puede ser negativo")

    paid_total = Decimal("0")
    for payment in payments:
        SalePayment.objects.create(sale=sale, method=payment["method"], amount=payment["amount"])
        paid_total += payment["amount"]

    if paid_total != total:
        raise ValidationError("El total de pagos no coincide con el total de la venta")

    sale.subtotal = subtotal
    sale.cost_total = cost_total
    sale.gross_profit = total - cost_total
    sale.total = total
    sale.save(update_fields=["subtotal", "cost_total", "gross_profit", "total", "updated_at"])

    cash_session.expected_amount += total
    cash_session.save(update_fields=["expected_amount", "updated_at"])

    return sale, True


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


def _group_expected_by_method(session: CashSession):
    rows = (
        SalePayment.objects.filter(sale__cash_session=session, sale__status=Sale.Status.COMPLETED)
        .values("method")
        .annotate(total=Sum("amount"))
    )
    breakdown = {row["method"]: Decimal(row["total"] or 0) for row in rows}
    for method, _ in SalePayment.Method.choices:
        breakdown.setdefault(method, Decimal("0"))
    return breakdown


@transaction.atomic
def close_cash_session_with_breakdown(*, session: CashSession, breakdown: dict, user):
    if not session.is_open:
        raise ValidationError("La caja ya esta cerrada")

    expected = _group_expected_by_method(session)
    provided = {key: Decimal(str(value or "0")) for key, value in breakdown.items()}
    for method, _ in SalePayment.Method.choices:
        provided.setdefault(method, Decimal("0"))

    expected_total = sum(expected.values(), Decimal("0"))
    closing_total = sum(provided.values(), Decimal("0"))
    difference_by_method = {method: provided[method] - expected[method] for method in expected}
    difference_amount = closing_total - expected_total

    session.closing_amount = closing_total
    session.expected_breakdown = {k: str(v) for k, v in expected.items()}
    session.closing_breakdown = {k: str(v) for k, v in provided.items()}
    session.difference_breakdown = {k: str(v) for k, v in difference_by_method.items()}
    session.difference_amount = difference_amount
    session.closed_by = user
    session.closed_at = timezone.now()
    session.is_open = False
    if difference_amount == 0:
        session.close_status = CashSession.CloseStatus.CLOSED
    else:
        session.close_status = CashSession.CloseStatus.PENDING_APPROVAL
    session.save(
        update_fields=[
            "closing_amount",
            "expected_breakdown",
            "closing_breakdown",
            "difference_breakdown",
            "difference_amount",
            "closed_by",
            "closed_at",
            "is_open",
            "close_status",
            "updated_at",
        ]
    )

    AuditLog.objects.create(
        action="CLOSE_CASH",
        model_name="CashSession",
        object_id=str(session.id),
        actor=user,
        metadata={
            "closing_amount": str(closing_total),
            "difference_amount": str(difference_amount),
            "close_status": session.close_status,
        },
    )
    return session


@transaction.atomic
def approve_cash_close(*, session: CashSession, user):
    if user.role not in {"SUPERADMIN", "SUPERVISOR"}:
        raise ValidationError("Solo supervisor o superadmin pueden aprobar cierres")
    if session.close_status != CashSession.CloseStatus.PENDING_APPROVAL:
        raise ValidationError("La caja no esta pendiente de aprobacion")

    session.close_status = CashSession.CloseStatus.CLOSED
    session.approved_by = user
    session.approved_at = timezone.now()
    session.save(update_fields=["close_status", "approved_by", "approved_at", "updated_at"])

    AuditLog.objects.create(
        action="APPROVE_CASH_CLOSE",
        model_name="CashSession",
        object_id=str(session.id),
        actor=user,
        metadata={"difference_amount": str(session.difference_amount)},
    )
    return session


@transaction.atomic
def reopen_cash_session(*, session: CashSession, reason: str, user):
    if user.role not in {"SUPERADMIN", "SUPERVISOR"}:
        raise ValidationError("Solo supervisor o superadmin pueden reabrir cajas")
    if session.is_open:
        raise ValidationError("La caja ya esta abierta")
    if session.close_status not in {
        CashSession.CloseStatus.CLOSED,
        CashSession.CloseStatus.PENDING_APPROVAL,
        CashSession.CloseStatus.REOPENED,
    }:
        raise ValidationError("Estado de cierre invalido para reapertura")

    session.is_open = True
    session.close_status = CashSession.CloseStatus.REOPENED
    session.reopened_by = user
    session.reopened_at = timezone.now()
    session.reopen_reason = reason
    session.save(
        update_fields=[
            "is_open",
            "close_status",
            "reopened_by",
            "reopened_at",
            "reopen_reason",
            "updated_at",
        ]
    )

    AuditLog.objects.create(
        action="REOPEN_CASH",
        model_name="CashSession",
        object_id=str(session.id),
        actor=user,
        metadata={"reason": reason},
    )
    return session

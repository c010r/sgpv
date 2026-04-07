from decimal import Decimal

from django.db import models

from core.models import TimeStampedModel


class CashRegister(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    bar = models.ForeignKey("settings_app.Bar", on_delete=models.PROTECT, related_name="cash_registers")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CashSession(TimeStampedModel):
    class CloseStatus(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pendiente Aprobacion"
        CLOSED = "CLOSED", "Cerrada"
        REOPENED = "REOPENED", "Reabierta"

    register = models.ForeignKey(CashRegister, on_delete=models.PROTECT, related_name="sessions")
    opened_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="opened_cash_sessions")
    closed_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="closed_cash_sessions"
    )
    opening_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    closing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_breakdown = models.JSONField(default=dict, blank=True)
    closing_breakdown = models.JSONField(default=dict, blank=True)
    difference_breakdown = models.JSONField(default=dict, blank=True)
    difference_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    close_status = models.CharField(max_length=20, choices=CloseStatus.choices, default=CloseStatus.OPEN)
    approved_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_cash_sessions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reopened_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="reopened_cash_sessions"
    )
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.CharField(max_length=255, blank=True)
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["register"], condition=models.Q(is_open=True), name="unique_open_cash_session_per_register"
            )
        ]


class Sale(TimeStampedModel):
    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completada"
        CANCELED = "CANCELED", "Cancelada"

    bar_session = models.ForeignKey("settings_app.BarSession", on_delete=models.PROTECT, related_name="sales")
    cash_session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name="sales")
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="created_sales")
    canceled_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="canceled_sales"
    )
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COMPLETED)
    cancel_reason = models.CharField(max_length=255, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    surcharge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))


class SaleItem(TimeStampedModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0"))
    line_cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    line_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class SalePayment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Efectivo"
        CARD = "CARD", "Tarjeta"
        TRANSFER = "TRANSFER", "Transferencia"

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=15, choices=Method.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

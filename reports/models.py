from django.db import models

from core.models import TimeStampedModel


class DailyFinancialSnapshot(TimeStampedModel):
    snapshot_date = models.DateField(unique=True)
    tickets = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discounts = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    surcharges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ["-snapshot_date"]


class AlertEvent(TimeStampedModel):
    class AlertType(models.TextChoices):
        LOW_STOCK = "LOW_STOCK", "Stock critico"
        CASH_DIFFERENCE = "CASH_DIFFERENCE", "Diferencia de caja"

    class Severity(models.TextChoices):
        LOW = "LOW", "Baja"
        MEDIUM = "MEDIUM", "Media"
        HIGH = "HIGH", "Alta"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        SENT = "SENT", "Enviada"
        RESOLVED = "RESOLVED", "Resuelta"

    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    message = models.CharField(max_length=255)
    dedup_key = models.CharField(max_length=120, blank=True, db_index=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict, blank=True)
    sent_via = models.CharField(max_length=20, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class AlertDispatchAttempt(TimeStampedModel):
    class Channel(models.TextChoices):
        WEBHOOK = "WEBHOOK", "Webhook"
        EMAIL = "EMAIL", "Email"
        SLACK = "SLACK", "Slack"
        TELEGRAM = "TELEGRAM", "Telegram"

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Exitoso"
        FAILED = "FAILED", "Fallido"

    alert = models.ForeignKey(AlertEvent, on_delete=models.CASCADE, related_name="dispatch_attempts")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    attempt_number = models.PositiveIntegerField(default=1)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

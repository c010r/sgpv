from django.db import models

from core.models import TimeStampedModel


class SystemConfiguration(TimeStampedModel):
    country_code = models.CharField(max_length=3, default="UY")
    currency_code = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=64, default="America/Montevideo")

    def __str__(self):
        return f"{self.country_code} - {self.currency_code}"


class Bar(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class BarSession(TimeStampedModel):
    bar = models.ForeignKey(Bar, on_delete=models.PROTECT, related_name="sessions")
    opened_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="opened_bar_sessions")
    closed_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="closed_bar_sessions"
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["-opened_at"]
        constraints = [
            models.UniqueConstraint(fields=["bar"], condition=models.Q(is_open=True), name="unique_open_session_per_bar")
        ]

    def __str__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        return f"{self.bar.name} - {status}"

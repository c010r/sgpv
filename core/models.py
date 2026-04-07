from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(TimeStampedModel):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("OPEN_BAR", "Open Bar"),
        ("CLOSE_BAR", "Close Bar"),
        ("OPEN_CASH", "Open Cash"),
        ("CLOSE_CASH", "Close Cash"),
        ("CANCEL_SALE", "Cancel Sale"),
        ("INVENTORY_ADJUSTMENT", "Inventory Adjustment"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("LOGIN_FAILED", "Login Failed"),
    ]

    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.model_name}:{self.object_id}"

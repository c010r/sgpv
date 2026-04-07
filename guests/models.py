from django.db import models

from core.models import TimeStampedModel


class GuestList(TimeStampedModel):
    name = models.CharField(max_length=150)
    event_date = models.DateField()
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="guest_lists")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "event_date"], name="unique_guest_list_per_event")]

    def __str__(self):
        return f"{self.name} ({self.event_date})"


class GuestEntry(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        ENTERED = "ENTERED", "Ingreso"
        REJECTED = "REJECTED", "Rechazado"
        NO_SHOW = "NO_SHOW", "No asistio"

    guest_list = models.ForeignKey(GuestList, on_delete=models.CASCADE, related_name="guests")
    full_name = models.CharField(max_length=150)
    document_id = models.CharField(max_length=50, blank=True)
    qr_code = models.CharField(max_length=120, unique=True)
    companions_allowed = models.PositiveSmallIntegerField(default=1)
    companions_used = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="guest_checkins"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["guest_list", "full_name"], name="unique_guest_per_list")
        ]

    def __str__(self):
        return f"{self.full_name} ({self.guest_list})"


class GuestImportJob(TimeStampedModel):
    class Status(models.TextChoices):
        PREVIEWED = "PREVIEWED", "Previsualizado"
        IMPORTED = "IMPORTED", "Importado"
        FAILED = "FAILED", "Fallido"

    guest_list = models.ForeignKey(GuestList, on_delete=models.CASCADE, related_name="import_jobs")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PREVIEWED)
    total_rows = models.PositiveIntegerField(default=0)
    created_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    imported_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="guest_import_jobs")


class GuestImportJobError(TimeStampedModel):
    job = models.ForeignKey(GuestImportJob, on_delete=models.CASCADE, related_name="errors")
    line_number = models.PositiveIntegerField()
    message = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict, blank=True)

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Superadmin"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        CAJERO = "CAJERO", "Cajero"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CAJERO)

    def __str__(self):
        return f"{self.username} ({self.role})"

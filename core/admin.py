from django.contrib import admin

from core.models import AuditLog

admin.site.register(AuditLog)

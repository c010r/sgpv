from django.contrib import admin

from reports.models import AlertEvent, DailyFinancialSnapshot


@admin.register(DailyFinancialSnapshot)
class DailyFinancialSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "tickets", "revenue", "cost", "profit", "margin_pct")
    list_filter = ("snapshot_date",)
    search_fields = ("snapshot_date",)
    ordering = ("-snapshot_date",)


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "alert_type", "severity", "status", "sent_via", "sent_at")
    list_filter = ("alert_type", "severity", "status", "sent_via")
    search_fields = ("message",)
    ordering = ("-created_at",)

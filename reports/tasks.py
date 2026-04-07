import json
from decimal import Decimal
from urllib import request as urlrequest

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Sum
from django.utils import timezone

from inventory.models import InventoryStock
from reports.models import AlertEvent, DailyFinancialSnapshot
from sales.models import CashSession, Sale


@shared_task
def summarize_sales_total():
    total = Sale.objects.filter(status=Sale.Status.COMPLETED).aggregate(total=Sum("total"))["total"]
    return str(total or 0)


@shared_task
def create_daily_financial_snapshot(target_date=None):
    if target_date:
        day = timezone.datetime.fromisoformat(target_date).date()
    else:
        day = timezone.localdate()

    qs = Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__date=day)
    agg = qs.aggregate(
        revenue=Sum("total"),
        subtotal=Sum("subtotal"),
        discounts=Sum("discount_amount"),
        surcharges=Sum("surcharge_amount"),
        cost=Sum("cost_total"),
        profit=Sum("gross_profit"),
        tickets=Count("id"),
    )
    revenue = Decimal(agg["revenue"] or 0)
    profit = Decimal(agg["profit"] or 0)
    margin = (profit / revenue * 100) if revenue else Decimal("0")

    snap, _ = DailyFinancialSnapshot.objects.update_or_create(
        snapshot_date=day,
        defaults={
            "tickets": agg["tickets"] or 0,
            "subtotal": Decimal(agg["subtotal"] or 0),
            "discounts": Decimal(agg["discounts"] or 0),
            "surcharges": Decimal(agg["surcharges"] or 0),
            "revenue": revenue,
            "cost": Decimal(agg["cost"] or 0),
            "profit": profit,
            "margin_pct": margin,
        },
    )
    return snap.id


def _send_alert(alert: AlertEvent):
    sent_channels = []
    webhook_url = getattr(settings, "ALERT_WEBHOOK_URL", "")
    email_to = getattr(settings, "ALERT_EMAIL_TO", "")

    if webhook_url:
        payload = json.dumps(
            {
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "payload": alert.payload,
                "created_at": alert.created_at.isoformat(),
            }
        ).encode("utf-8")
        req = urlrequest.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=5):
                sent_channels.append("webhook")
        except Exception:
            pass

    if email_to:
        try:
            send_mail(
                subject=f"[SGPV Alert] {alert.alert_type} {alert.severity}",
                message=f"{alert.message}\n\n{json.dumps(alert.payload, ensure_ascii=False, indent=2)}",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "sgpv@localhost"),
                recipient_list=[e.strip() for e in email_to.split(",") if e.strip()],
                fail_silently=True,
            )
            sent_channels.append("email")
        except Exception:
            pass

    if sent_channels:
        alert.status = AlertEvent.Status.SENT
        alert.sent_via = ",".join(sent_channels)
        alert.sent_at = timezone.now()
        alert.save(update_fields=["status", "sent_via", "sent_at", "updated_at"])


@shared_task
def scan_and_dispatch_alerts(low_stock_threshold=10, cash_diff_threshold=0):
    created_ids = []

    low_stocks = InventoryStock.objects.filter(
        location__location_type="BAR",
        quantity__lte=Decimal(str(low_stock_threshold)),
    ).select_related("location", "product")

    for stock in low_stocks:
        alert = AlertEvent.objects.create(
            alert_type=AlertEvent.AlertType.LOW_STOCK,
            severity=AlertEvent.Severity.HIGH if stock.quantity <= 0 else AlertEvent.Severity.MEDIUM,
            message=f"Stock critico {stock.product.name} en {stock.location.name}: {stock.quantity}",
            payload={
                "location_id": stock.location_id,
                "location_name": stock.location.name,
                "product_id": stock.product_id,
                "product_name": stock.product.name,
                "quantity": str(stock.quantity),
            },
        )
        _send_alert(alert)
        created_ids.append(alert.id)

    cash_sessions = CashSession.objects.filter(
        close_status=CashSession.CloseStatus.PENDING_APPROVAL,
        difference_amount__gt=Decimal(str(cash_diff_threshold)),
    ).select_related("register")

    for session in cash_sessions:
        alert = AlertEvent.objects.create(
            alert_type=AlertEvent.AlertType.CASH_DIFFERENCE,
            severity=AlertEvent.Severity.HIGH,
            message=f"Diferencia de caja pendiente en {session.register.name}: {session.difference_amount}",
            payload={
                "cash_session_id": session.id,
                "register_id": session.register_id,
                "register_name": session.register.name,
                "difference_amount": str(session.difference_amount),
            },
        )
        _send_alert(alert)
        created_ids.append(alert.id)

    return created_ids

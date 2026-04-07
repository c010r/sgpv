from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from inventory.services import ensure_bar_inventory
from settings_app.models import BarSession


@transaction.atomic
def open_bar_session(*, bar, user):
    session = BarSession.objects.create(bar=bar, opened_by=user)
    ensure_bar_inventory(bar)
    AuditLog.objects.create(
        action="OPEN_BAR",
        model_name="BarSession",
        object_id=str(session.id),
        actor=user,
        metadata={"bar_id": bar.id},
    )
    return session


@transaction.atomic
def close_bar_session(*, session: BarSession, user):
    session.is_open = False
    session.closed_at = timezone.now()
    session.closed_by = user
    session.save(update_fields=["is_open", "closed_at", "closed_by", "updated_at"])

    AuditLog.objects.create(
        action="CLOSE_BAR",
        model_name="BarSession",
        object_id=str(session.id),
        actor=user,
        metadata={"bar_id": session.bar_id},
    )
    return session

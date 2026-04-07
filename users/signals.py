from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from core.models import AuditLog


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    AuditLog.objects.create(
        action="LOGIN",
        model_name="AuthSignal",
        object_id=str(user.id),
        actor=user,
        metadata={"ip": request.META.get("REMOTE_ADDR", "") if request else ""},
    )


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):
    actor = user if getattr(user, "is_authenticated", False) else None
    object_id = str(user.id) if actor else "anonymous"
    AuditLog.objects.create(
        action="LOGOUT",
        model_name="AuthSignal",
        object_id=object_id,
        actor=actor,
        metadata={"ip": request.META.get("REMOTE_ADDR", "") if request else ""},
    )


@receiver(user_login_failed)
def handle_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", "unknown") if isinstance(credentials, dict) else "unknown"
    AuditLog.objects.create(
        action="LOGIN_FAILED",
        model_name="AuthSignal",
        object_id=str(username),
        metadata={"username": username, "ip": request.META.get("REMOTE_ADDR", "") if request else ""},
    )

from unittest import mock

import pytest

from reports.models import AlertDispatchAttempt, AlertEvent
from reports.tasks import _send_alert


class _DummyResponse:
    def __init__(self, status=200, body=b"ok"):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


@pytest.mark.django_db
def test_alert_webhook_retry_then_success(settings):
    settings.ALERT_WEBHOOK_URL = "https://example.org/hook"
    settings.ALERT_EMAIL_TO = ""
    settings.ALERT_SLACK_WEBHOOK_URL = ""
    settings.ALERT_TELEGRAM_BOT_TOKEN = ""
    settings.ALERT_TELEGRAM_CHAT_ID = ""
    settings.ALERT_MAX_RETRIES = 3

    alert = AlertEvent.objects.create(
        alert_type=AlertEvent.AlertType.LOW_STOCK,
        severity=AlertEvent.Severity.HIGH,
        message="Alerta de prueba",
        payload={"k": "v"},
    )

    with mock.patch(
        "reports.tasks.urlrequest.urlopen",
        side_effect=[Exception("network error"), _DummyResponse(status=200, body=b"ok")],
    ):
        _send_alert(alert)

    alert.refresh_from_db()
    attempts = list(AlertDispatchAttempt.objects.filter(alert=alert).order_by("attempt_number"))

    assert alert.status == AlertEvent.Status.SENT
    assert "webhook" in alert.sent_via
    assert len(attempts) == 2
    assert attempts[0].status == AlertDispatchAttempt.Status.FAILED
    assert attempts[1].status == AlertDispatchAttempt.Status.SUCCESS


@pytest.mark.django_db
def test_alert_webhook_all_retries_fail(settings):
    settings.ALERT_WEBHOOK_URL = "https://example.org/hook"
    settings.ALERT_EMAIL_TO = ""
    settings.ALERT_SLACK_WEBHOOK_URL = ""
    settings.ALERT_TELEGRAM_BOT_TOKEN = ""
    settings.ALERT_TELEGRAM_CHAT_ID = ""
    settings.ALERT_MAX_RETRIES = 2

    alert = AlertEvent.objects.create(
        alert_type=AlertEvent.AlertType.CASH_DIFFERENCE,
        severity=AlertEvent.Severity.HIGH,
        message="Alerta de caja",
        payload={"x": "1"},
    )

    with mock.patch("reports.tasks.urlrequest.urlopen", side_effect=Exception("down")):
        _send_alert(alert)

    alert.refresh_from_db()
    attempts = list(AlertDispatchAttempt.objects.filter(alert=alert).order_by("attempt_number"))

    assert alert.status == AlertEvent.Status.OPEN
    assert alert.sent_via == ""
    assert len(attempts) == 2
    assert all(a.status == AlertDispatchAttempt.Status.FAILED for a in attempts)

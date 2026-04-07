from unittest import mock

import pytest
from rest_framework.test import APIClient

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


@pytest.mark.django_db
def test_webhook_includes_hmac_headers_when_signing_enabled(settings):
    settings.ALERT_WEBHOOK_URL = "https://example.org/hook"
    settings.ALERT_WEBHOOK_SIGNING_SECRET = "secret123"
    settings.ALERT_WEBHOOK_SIGNATURE_HEADER = "X-SGPV-Signature"
    settings.ALERT_WEBHOOK_TIMESTAMP_HEADER = "X-SGPV-Timestamp"
    settings.ALERT_EMAIL_TO = ""
    settings.ALERT_SLACK_WEBHOOK_URL = ""
    settings.ALERT_TELEGRAM_BOT_TOKEN = ""
    settings.ALERT_TELEGRAM_CHAT_ID = ""
    settings.ALERT_MAX_RETRIES = 1

    alert = AlertEvent.objects.create(
        alert_type=AlertEvent.AlertType.LOW_STOCK,
        severity=AlertEvent.Severity.HIGH,
        message="Firma webhook",
        payload={"a": 1},
    )

    captured_headers = {}

    def _capture(req, timeout=5):
        _ = timeout
        captured_headers.update({k.lower(): v for k, v in req.header_items()})
        return _DummyResponse(status=200, body=b"ok")

    with mock.patch("reports.tasks.urlrequest.urlopen", side_effect=_capture):
        _send_alert(alert)

    assert "x-sgpv-signature" in captured_headers
    assert captured_headers["x-sgpv-signature"].startswith("sha256=")
    assert "x-sgpv-timestamp" in captured_headers


@pytest.mark.django_db
def test_supervisor_can_query_alert_attempts_with_filters(supervisor, settings):
    settings.ALERT_WEBHOOK_URL = "https://example.org/hook"
    settings.ALERT_EMAIL_TO = ""
    settings.ALERT_SLACK_WEBHOOK_URL = ""
    settings.ALERT_TELEGRAM_BOT_TOKEN = ""
    settings.ALERT_TELEGRAM_CHAT_ID = ""
    settings.ALERT_MAX_RETRIES = 2

    alert = AlertEvent.objects.create(
        alert_type=AlertEvent.AlertType.LOW_STOCK,
        severity=AlertEvent.Severity.MEDIUM,
        message="Stock bajo",
        payload={"p": 1},
    )

    with mock.patch("reports.tasks.urlrequest.urlopen", side_effect=Exception("down")):
        _send_alert(alert)

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get(
        f"/api/reportes/alertas/{alert.id}/attempts/?channel=WEBHOOK&status=FAILED&order_by=attempt_number&limit=1&offset=1",
    )
    assert response.status_code == 200
    assert response.data["alert_id"] == alert.id
    assert response.data["count"] == 1
    assert response.data["limit"] == 1
    assert response.data["offset"] == 1
    assert all(a["channel"] == "WEBHOOK" for a in response.data["attempts"])
    assert all(a["status"] == "FAILED" for a in response.data["attempts"])
    assert response.data["attempts"][0]["attempt_number"] == 2


@pytest.mark.django_db
def test_cajero_cannot_query_alert_attempts(cajero):
    alert = AlertEvent.objects.create(
        alert_type=AlertEvent.AlertType.CASH_DIFFERENCE,
        severity=AlertEvent.Severity.HIGH,
        message="Caja descuadre",
        payload={"d": "1"},
    )
    client = APIClient()
    client.force_authenticate(user=cajero)
    response = client.get(f"/api/reportes/alertas/{alert.id}/attempts/")
    assert response.status_code == 403

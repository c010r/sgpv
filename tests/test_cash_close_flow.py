from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from sales.models import CashRegister
from sales.services import open_cash_session
from settings_app.models import Bar


@pytest.mark.django_db
def test_cash_close_with_difference_requires_approval(supervisor, cajero):
    bar = Bar.objects.create(name="Bar Close Flow")
    register = CashRegister.objects.create(name="Caja Close Flow", bar=bar)
    session = open_cash_session(register=register, opening_amount=Decimal("100"), user=cajero)

    client = APIClient()
    client.force_authenticate(user=cajero)

    close_resp = client.post(
        f"/api/sesiones-caja/{session.id}/close/",
        {"breakdown": {"CASH": "10.00", "CARD": "0.00", "TRANSFER": "0.00"}},
        format="json",
    )
    assert close_resp.status_code == 200
    assert close_resp.data["close_status"] == "PENDING_APPROVAL"

    approve_as_cajero = client.post(f"/api/sesiones-caja/{session.id}/approve_close/", {"approve": True}, format="json")
    assert approve_as_cajero.status_code == 403

    client.force_authenticate(user=supervisor)
    approve_resp = client.post(f"/api/sesiones-caja/{session.id}/approve_close/", {"approve": True}, format="json")
    assert approve_resp.status_code == 200
    assert approve_resp.data["close_status"] == "CLOSED"


@pytest.mark.django_db
def test_cash_reopen_only_supervisor(supervisor, cajero):
    bar = Bar.objects.create(name="Bar Reopen Flow")
    register = CashRegister.objects.create(name="Caja Reopen Flow", bar=bar)
    session = open_cash_session(register=register, opening_amount=Decimal("50"), user=cajero)

    client = APIClient()
    client.force_authenticate(user=cajero)
    client.post(
        f"/api/sesiones-caja/{session.id}/close/",
        {"breakdown": {"CASH": "0.00", "CARD": "0.00", "TRANSFER": "0.00"}},
        format="json",
    )

    bad = client.post(f"/api/sesiones-caja/{session.id}/reopen/", {"reason": "need reopen"}, format="json")
    assert bad.status_code == 403

    client.force_authenticate(user=supervisor)
    ok = client.post(f"/api/sesiones-caja/{session.id}/reopen/", {"reason": "need reopen"}, format="json")
    assert ok.status_code == 200
    assert ok.data["is_open"] is True
    assert ok.data["close_status"] == "REOPENED"

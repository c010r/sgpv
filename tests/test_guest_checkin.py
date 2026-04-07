import pytest
from rest_framework.test import APIClient

from guests.models import GuestEntry, GuestList


@pytest.mark.django_db
def test_guest_qr_cannot_reenter(supervisor, cajero):
    guest_list = GuestList.objects.create(name="Lista Test", event_date="2026-04-12", created_by=supervisor)
    guest = GuestEntry.objects.create(
        guest_list=guest_list,
        full_name="Invitado Uno",
        qr_code="QR-TEST-0001",
        companions_allowed=1,
    )

    client = APIClient()
    client.force_authenticate(user=cajero)

    first = client.post("/api/invitados/checkin/", {"qr_code": guest.qr_code, "companions_used": 1}, format="json")
    assert first.status_code == 200
    guest.refresh_from_db()
    assert guest.status == GuestEntry.Status.ENTERED

    second = client.post("/api/invitados/checkin/", {"qr_code": guest.qr_code, "companions_used": 0}, format="json")
    assert second.status_code == 400
    assert "ya ingreso" in second.data["detail"].lower()

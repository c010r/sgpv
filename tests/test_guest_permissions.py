import pytest
from rest_framework.test import APIClient

from guests.models import GuestList


@pytest.mark.django_db
def test_cajero_cannot_create_guest_entry(supervisor, cajero):
    guest_list = GuestList.objects.create(name="Perm Lista", event_date="2026-04-12", created_by=supervisor)

    client = APIClient()
    client.force_authenticate(user=cajero)
    response = client.post(
        "/api/invitados/",
        {
            "guest_list": guest_list.id,
            "full_name": "Intento Cajero",
            "qr_code": "QR-PERM-01",
            "companions_allowed": 1,
        },
        format="json",
    )

    assert response.status_code == 403

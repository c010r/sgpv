import pytest
from rest_framework.test import APIClient

from settings_app.models import Bar


@pytest.mark.django_db
def test_anonymous_cannot_access_reports_dashboard():
    client = APIClient()
    response = client.get("/api/reportes/dashboard/")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_cajero_cannot_start_stock_count(supervisor, cajero):
    bar = Bar.objects.create(name="RBAC StockCount")
    location = bar.inventory_location if hasattr(bar, "inventory_location") else None
    if not location:
        from settings_app.services import open_bar_session

        open_bar_session(bar=bar, user=supervisor)
        location = bar.inventory_location

    client = APIClient()
    client.force_authenticate(user=cajero)
    response = client.post("/api/inventario/conteos/start/", {"location_id": location.id}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_supervisor_can_start_stock_count(supervisor):
    bar = Bar.objects.create(name="RBAC StockCount 2")
    from settings_app.services import open_bar_session

    open_bar_session(bar=bar, user=supervisor)
    location = bar.inventory_location

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.post("/api/inventario/conteos/start/", {"location_id": location.id}, format="json")
    assert response.status_code == 201

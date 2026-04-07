from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import InventoryLocation, InventoryStock, Product
from sales.models import CashRegister, CashSession, Sale
from settings_app.models import Bar, BarSession


@pytest.mark.django_db
def test_dashboard_returns_hourly_metrics_and_critical_stock(supervisor):
    bar = Bar.objects.create(name="Bar Dashboard")
    bar_session = BarSession.objects.create(bar=bar, opened_by=supervisor, is_open=True)
    register = CashRegister.objects.create(name="Caja Dashboard", bar=bar)
    cash_session = CashSession.objects.create(register=register, opened_by=supervisor, opening_amount=Decimal("100"), is_open=True)

    now = timezone.now()
    sale_recent = Sale.objects.create(
        bar_session=bar_session,
        cash_session=cash_session,
        created_by=supervisor,
        total=Decimal("20.00"),
        status=Sale.Status.COMPLETED,
    )
    sale_old = Sale.objects.create(
        bar_session=bar_session,
        cash_session=cash_session,
        created_by=supervisor,
        total=Decimal("15.00"),
        status=Sale.Status.COMPLETED,
    )
    Sale.objects.filter(id=sale_recent.id).update(created_at=now - timedelta(hours=2))
    Sale.objects.filter(id=sale_old.id).update(created_at=now - timedelta(hours=6))

    location = InventoryLocation.objects.create(name="Barra Dashboard", location_type=InventoryLocation.LocationType.BAR, bar=bar)
    low_product = Product.objects.create(
        name="Limon",
        sku="LIMON-01",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("1.00"),
        cost_price=Decimal("0.30"),
    )
    InventoryStock.objects.create(location=location, product=low_product, quantity=Decimal("3"))

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get("/api/reportes/dashboard/?low_stock_threshold=5")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["hourly_sales_last_24h"]) == 24
    assert any(int(slot["tickets"]) > 0 for slot in payload["hourly_sales_last_24h"])
    assert len(payload["critical_stock_by_bar"]) >= 1
    first_group = payload["critical_stock_by_bar"][0]
    assert first_group["bar_name"] == "Bar Dashboard"
    assert first_group["items_count"] >= 1

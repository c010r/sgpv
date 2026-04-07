from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from inventory.models import InventoryStock, Product
from inventory.services import ensure_central_inventory, transfer_stock
from settings_app.models import Bar
from settings_app.services import open_bar_session


@pytest.mark.django_db
def test_stock_count_apply_adjusts_inventory(supervisor):
    bar = Bar.objects.create(name="Bar Count")
    open_bar_session(bar=bar, user=supervisor)
    product = Product.objects.create(
        name="Count Product",
        sku="COUNT-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("1.00"),
        cost_price=Decimal("0.50"),
    )

    central, _ = ensure_central_inventory()
    central_stock, _ = InventoryStock.objects.get_or_create(location=central, product=product)
    central_stock.quantity = Decimal("50")
    central_stock.save(update_fields=["quantity", "updated_at"])

    transfer_stock(
        source=central,
        destination=bar.inventory_location,
        product=product,
        quantity=Decimal("10"),
        user=supervisor,
        reason="count setup",
    )

    client = APIClient()
    client.force_authenticate(user=supervisor)

    start = client.post("/api/inventario/conteos/start/", {"location_id": bar.inventory_location.id}, format="json")
    assert start.status_code == 201
    session_id = start.data["id"]

    close = client.post(
        f"/api/inventario/conteos/{session_id}/close/",
        {"counted": {str(product.id): "7"}},
        format="json",
    )
    assert close.status_code == 200

    apply_resp = client.post(f"/api/inventario/conteos/{session_id}/apply/", {}, format="json")
    assert apply_resp.status_code == 200
    assert apply_resp.data["status"] == "APPLIED"

    stock = InventoryStock.objects.get(location=bar.inventory_location, product=product)
    assert stock.quantity == Decimal("7")

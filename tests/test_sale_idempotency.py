from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from inventory.models import InventoryStock, Product
from inventory.services import ensure_central_inventory, transfer_stock
from sales.models import CashRegister, Sale
from sales.services import open_cash_session
from settings_app.models import Bar
from settings_app.services import open_bar_session


@pytest.mark.django_db
def test_create_sale_is_idempotent(supervisor, cajero):
    bar = Bar.objects.create(name="Bar Idempotency")
    product = Product.objects.create(
        name="Idempotent Product",
        sku="IDEMP-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("4.00"),
        cost_price=Decimal("1.00"),
        is_active=True,
    )

    bar_session = open_bar_session(bar=bar, user=supervisor)
    central, _ = ensure_central_inventory()
    central_stock, _ = InventoryStock.objects.get_or_create(location=central, product=product)
    central_stock.quantity = Decimal("20")
    central_stock.save(update_fields=["quantity", "updated_at"])

    transfer_stock(
        source=central,
        destination=bar.inventory_location,
        product=product,
        quantity=Decimal("10"),
        user=supervisor,
        reason="idempotency test",
    )

    register = CashRegister.objects.create(name="Caja Idempotency", bar=bar)
    cash_session = open_cash_session(register=register, opening_amount=Decimal("30"), user=cajero)

    client = APIClient()
    client.force_authenticate(user=cajero)

    payload = {
        "bar_session_id": bar_session.id,
        "cash_session_id": cash_session.id,
        "idempotency_key": "REQ-12345",
        "discount_amount": "1.00",
        "surcharge_amount": "0.00",
        "items": [{"product_id": product.id, "quantity": "2", "unit_price": "4.00"}],
        "payments": [{"method": "CASH", "amount": "7.00"}],
    }

    first = client.post("/api/ventas/create_sale/", payload, format="json")
    second = client.post("/api/ventas/create_sale/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Sale.objects.count() == 1

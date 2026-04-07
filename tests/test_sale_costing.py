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
def test_sale_persists_cost_and_profit_fields(supervisor, cajero):
    bar = Bar.objects.create(name="Bar Cost")
    bar_session = open_bar_session(bar=bar, user=supervisor)

    product = Product.objects.create(
        name="Cost Product",
        sku="COST-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("10.00"),
        cost_price=Decimal("3.00"),
        is_active=True,
    )

    central, _ = ensure_central_inventory()
    s, _ = InventoryStock.objects.get_or_create(location=central, product=product)
    s.quantity = Decimal("20")
    s.save(update_fields=["quantity", "updated_at"])
    transfer_stock(source=central, destination=bar.inventory_location, product=product, quantity=Decimal("10"), user=supervisor)

    register = CashRegister.objects.create(name="Caja Cost", bar=bar)
    cash = open_cash_session(register=register, opening_amount=Decimal("100"), user=cajero)

    client = APIClient()
    client.force_authenticate(user=cajero)
    resp = client.post(
        "/api/ventas/create_sale/",
        {
            "bar_session_id": bar_session.id,
            "cash_session_id": cash.id,
            "items": [{"product_id": product.id, "quantity": "2", "unit_price": "10.00"}],
            "payments": [{"method": "CASH", "amount": "20.00"}],
        },
        format="json",
    )
    assert resp.status_code == 201

    sale = Sale.objects.get(id=resp.data["id"])
    assert sale.cost_total == Decimal("6.00")
    assert sale.gross_profit == Decimal("14.00")

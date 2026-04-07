from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from inventory.models import InventoryStock, Product
from inventory.services import ensure_central_inventory, transfer_stock
from sales.models import CashRegister
from sales.services import create_sale, open_cash_session
from settings_app.models import Bar
from settings_app.services import open_bar_session


def _build_sale(supervisor, cajero):
    bar = Bar.objects.create(name="Bar API Perm")
    product = Product.objects.create(
        name="Bebida API Perm",
        sku="API-PERM-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("7.00"),
        cost_price=Decimal("2.00"),
        is_active=True,
    )

    bar_session = open_bar_session(bar=bar, user=supervisor)
    central, _ = ensure_central_inventory()
    central_stock, _ = InventoryStock.objects.get_or_create(location=central, product=product)
    central_stock.quantity = Decimal("50")
    central_stock.save(update_fields=["quantity", "updated_at"])

    transfer_stock(
        source=central,
        destination=bar.inventory_location,
        product=product,
        quantity=Decimal("20"),
        user=supervisor,
        reason="setup perms",
    )

    register = CashRegister.objects.create(name="Caja API Perm", bar=bar)
    cash_session = open_cash_session(register=register, opening_amount=Decimal("100"), user=cajero)
    sale, _ = create_sale(
        bar_session=bar_session,
        cash_session=cash_session,
        items=[{"product": product, "quantity": Decimal("1"), "unit_price": Decimal("7.00")}],
        payments=[{"method": "CASH", "amount": Decimal("7.00")}],
        user=cajero,
    )
    return sale


@pytest.mark.django_db
def test_cajero_cannot_cancel_sale_endpoint(supervisor, cajero):
    sale = _build_sale(supervisor, cajero)

    client = APIClient()
    client.force_authenticate(user=cajero)
    response = client.post(f"/api/ventas/{sale.id}/cancel/", {"reason": "no autorizado"}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_supervisor_can_cancel_sale_endpoint(supervisor, cajero):
    sale = _build_sale(supervisor, cajero)

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.post(f"/api/ventas/{sale.id}/cancel/", {"reason": "autoriza"}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "CANCELED"

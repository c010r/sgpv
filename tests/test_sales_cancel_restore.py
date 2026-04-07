from decimal import Decimal

import pytest

from inventory.models import InventoryStock, Product
from inventory.services import ensure_central_inventory, transfer_stock
from sales.models import CashRegister
from sales.services import cancel_sale, create_sale, open_cash_session
from settings_app.models import Bar
from settings_app.services import open_bar_session


@pytest.mark.django_db
def test_cancel_sale_restores_inventory(supervisor, cajero):
    bar = Bar.objects.create(name="Bar Test")
    product = Product.objects.create(
        name="Cerveza Test",
        sku="TEST-BEER-1",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("5.00"),
        cost_price=Decimal("1.00"),
        is_active=True,
    )

    bar_session = open_bar_session(bar=bar, user=supervisor)
    bar_location = bar.inventory_location

    central, _ = ensure_central_inventory()
    central_stock, _ = InventoryStock.objects.get_or_create(location=central, product=product)
    central_stock.quantity = Decimal("100")
    central_stock.save(update_fields=["quantity", "updated_at"])

    transfer_stock(
        source=central,
        destination=bar_location,
        product=product,
        quantity=Decimal("10"),
        user=supervisor,
        reason="Carga test",
    )

    register = CashRegister.objects.create(name="Caja Test", bar=bar)
    cash_session = open_cash_session(register=register, opening_amount=Decimal("100"), user=cajero)

    sale, _ = create_sale(
        bar_session=bar_session,
        cash_session=cash_session,
        items=[{"product": product, "quantity": Decimal("2"), "unit_price": Decimal("5.00")}],
        payments=[{"method": "CASH", "amount": Decimal("10.00")}],
        user=cajero,
    )

    bar_stock = InventoryStock.objects.get(location=bar_location, product=product)
    cash_session.refresh_from_db()
    assert bar_stock.quantity == Decimal("8")
    assert cash_session.expected_amount == Decimal("10.00")

    sale = cancel_sale(sale=sale, reason="Anulacion test", user=supervisor)
    bar_stock.refresh_from_db()
    cash_session.refresh_from_db()

    assert sale.status == sale.Status.CANCELED
    assert bar_stock.quantity == Decimal("10")
    assert cash_session.expected_amount == Decimal("0.00")

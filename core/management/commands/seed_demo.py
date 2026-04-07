from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from guests.models import GuestEntry, GuestList
from inventory.models import InventoryLocation, InventoryStock, Product, Recipe, RecipeItem
from inventory.services import ensure_central_inventory, transfer_stock
from sales.models import CashRegister
from sales.services import create_sale, open_cash_session
from settings_app.models import Bar
from settings_app.services import open_bar_session


class Command(BaseCommand):
    help = "Carga datos demo para SGPV"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        superadmin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"role": "SUPERADMIN", "is_staff": True, "is_superuser": True, "email": "admin@demo.com"},
        )
        superadmin.set_password("admin123")
        superadmin.save()

        supervisor, _ = User.objects.get_or_create(username="supervisor", defaults={"role": "SUPERVISOR"})
        supervisor.set_password("super123")
        supervisor.save()

        cajero, _ = User.objects.get_or_create(username="cajero", defaults={"role": "CAJERO"})
        cajero.set_password("cajero123")
        cajero.save()

        bar, _ = Bar.objects.get_or_create(name="Barra Principal", defaults={"is_active": True})
        bar_session = bar.sessions.filter(is_open=True).first() or open_bar_session(bar=bar, user=supervisor)

        central, _ = ensure_central_inventory()

        p_ron, _ = Product.objects.get_or_create(
            sku="RON-001",
            defaults={
                "name": "Ron Blanco",
                "unit": "ML",
                "sale_price": Decimal("0"),
                "cost_price": Decimal("0.08"),
                "is_active": True,
            },
        )
        p_cola, _ = Product.objects.get_or_create(
            sku="COLA-001",
            defaults={
                "name": "Gaseosa Cola",
                "unit": "ML",
                "sale_price": Decimal("0"),
                "cost_price": Decimal("0.02"),
                "is_active": True,
            },
        )
        p_vaso, _ = Product.objects.get_or_create(
            sku="VASO-001",
            defaults={
                "name": "Vaso Plastico",
                "unit": "UNIT",
                "sale_price": Decimal("0"),
                "cost_price": Decimal("0.10"),
                "is_active": True,
            },
        )
        p_cuba, _ = Product.objects.get_or_create(
            sku="COCK-001",
            defaults={
                "name": "Cuba Libre",
                "unit": "UNIT",
                "sale_price": Decimal("8.00"),
                "cost_price": Decimal("0"),
                "is_active": True,
            },
        )
        p_cerveza, _ = Product.objects.get_or_create(
            sku="CERVE-001",
            defaults={
                "name": "Cerveza",
                "unit": "UNIT",
                "sale_price": Decimal("5.00"),
                "cost_price": Decimal("1.20"),
                "is_active": True,
            },
        )

        recipe, _ = Recipe.objects.get_or_create(name="Receta Cuba Libre", sale_product=p_cuba)
        RecipeItem.objects.get_or_create(recipe=recipe, ingredient=p_ron, defaults={"quantity": Decimal("50")})
        RecipeItem.objects.get_or_create(recipe=recipe, ingredient=p_cola, defaults={"quantity": Decimal("120")})
        RecipeItem.objects.get_or_create(recipe=recipe, ingredient=p_vaso, defaults={"quantity": Decimal("1")})

        for product, qty in [
            (p_ron, Decimal("50000")),
            (p_cola, Decimal("40000")),
            (p_vaso, Decimal("500")),
            (p_cerveza, Decimal("300")),
        ]:
            stock, _ = InventoryStock.objects.get_or_create(location=central, product=product)
            stock.quantity = qty
            stock.save(update_fields=["quantity", "updated_at"])

        bar_location = InventoryLocation.objects.get(bar=bar)
        for product, target_qty in [
            (p_ron, Decimal("10000")),
            (p_cola, Decimal("8000")),
            (p_vaso, Decimal("120")),
            (p_cerveza, Decimal("80")),
        ]:
            bar_stock, _ = InventoryStock.objects.get_or_create(location=bar_location, product=product)
            missing = target_qty - bar_stock.quantity
            if missing > 0:
                transfer_stock(
                    source=central,
                    destination=bar_location,
                    product=product,
                    quantity=missing,
                    user=supervisor,
                    reason="Carga inicial demo",
                )

        register, _ = CashRegister.objects.get_or_create(name="Caja Principal", defaults={"bar": bar, "is_active": True})
        if register.bar_id != bar.id:
            register.bar = bar
            register.save(update_fields=["bar", "updated_at"])

        cash_session = register.sessions.filter(is_open=True).first() or open_cash_session(
            register=register, opening_amount=Decimal("200"), user=cajero
        )

        if not cash_session.sales.exists():
            create_sale(
                bar_session=bar_session,
                cash_session=cash_session,
                items=[
                    {"product": p_cuba, "quantity": Decimal("2"), "unit_price": Decimal("8.00")},
                    {"product": p_cerveza, "quantity": Decimal("3"), "unit_price": Decimal("5.00")},
                ],
                payments=[
                    {"method": "CARD", "amount": Decimal("16.00")},
                    {"method": "CASH", "amount": Decimal("15.00")},
                ],
                user=cajero,
            )

        glist, _ = GuestList.objects.get_or_create(name="Lista Sabado", event_date="2026-04-11", defaults={"created_by": supervisor})
        GuestEntry.objects.get_or_create(
            guest_list=glist,
            full_name="Invitado Demo",
            defaults={"qr_code": "QR-DEMO-0001", "companions_allowed": 1, "document_id": "DOC123"},
        )

        self.stdout.write(self.style.SUCCESS("Seed demo completado."))
        self.stdout.write("Usuarios: admin/admin123, supervisor/super123, cajero/cajero123")

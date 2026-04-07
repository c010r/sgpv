from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from inventory.models import InventoryLocation, InventoryStock, Product
from reports.models import AlertEvent
from sales.models import CashRegister, CashSession, Sale
from settings_app.models import Bar, BarSession


@pytest.mark.django_db
def test_supervisor_can_generate_snapshot_sync_and_list(supervisor):
    bar = Bar.objects.create(name="Bar Snapshot")
    bar_session = BarSession.objects.create(bar=bar, opened_by=supervisor, is_open=True)
    register = CashRegister.objects.create(name="Caja Snapshot", bar=bar)
    cash_session = CashSession.objects.create(register=register, opened_by=supervisor, opening_amount=Decimal("100"))
    Sale.objects.create(
        bar_session=bar_session,
        cash_session=cash_session,
        created_by=supervisor,
        status=Sale.Status.COMPLETED,
        subtotal=Decimal("100.00"),
        discount_amount=Decimal("5.00"),
        surcharge_amount=Decimal("2.00"),
        cost_total=Decimal("40.00"),
        gross_profit=Decimal("57.00"),
        total=Decimal("97.00"),
    )

    client = APIClient()
    client.force_authenticate(user=supervisor)
    create_resp = client.post("/api/reportes/snapshots/", {"sync": True}, format="json")

    assert create_resp.status_code == 200
    assert create_resp.data["snapshot_id"] is not None

    list_resp = client.get("/api/reportes/snapshots/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) >= 1
    first = list_resp.data[0]
    assert first["revenue"] == "97.00"
    assert first["cost"] == "40.00"
    assert first["profit"] == "57.00"


@pytest.mark.django_db
def test_supervisor_can_scan_alerts_sync(supervisor):
    bar = Bar.objects.create(name="Bar Alertas")
    location = InventoryLocation.objects.create(
        name="Inventario Bar Alertas",
        location_type=InventoryLocation.LocationType.BAR,
        bar=bar,
    )
    product = Product.objects.create(
        name="Gin Alerta",
        sku="GIN-ALERTA-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("10.00"),
        cost_price=Decimal("3.00"),
    )
    InventoryStock.objects.create(location=location, product=product, quantity=Decimal("1.000"))

    register = CashRegister.objects.create(name="Caja Alertas", bar=bar)
    CashSession.objects.create(
        register=register,
        opened_by=supervisor,
        opening_amount=Decimal("50.00"),
        difference_amount=Decimal("5.00"),
        close_status=CashSession.CloseStatus.PENDING_APPROVAL,
        is_open=False,
    )

    client = APIClient()
    client.force_authenticate(user=supervisor)
    scan_resp = client.post(
        "/api/reportes/alertas/",
        {"sync": True, "low_stock_threshold": 2, "cash_diff_threshold": 0},
        format="json",
    )
    assert scan_resp.status_code == 200
    assert len(scan_resp.data["alert_ids"]) >= 2

    list_resp = client.get("/api/reportes/alertas/")
    assert list_resp.status_code == 200
    alert_types = {row["alert_type"] for row in list_resp.data["results"]}
    assert "LOW_STOCK" in alert_types
    assert "CASH_DIFFERENCE" in alert_types


@pytest.mark.django_db
def test_alert_scan_deduplicates_in_window(supervisor, settings):
    settings.ALERT_DEDUP_WINDOW_MINUTES = 60

    bar = Bar.objects.create(name="Bar Dedup")
    location = InventoryLocation.objects.create(
        name="Inventario Bar Dedup",
        location_type=InventoryLocation.LocationType.BAR,
        bar=bar,
    )
    product = Product.objects.create(
        name="Vodka Dedup",
        sku="VODKA-DEDUP-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("12.00"),
        cost_price=Decimal("4.00"),
    )
    InventoryStock.objects.create(location=location, product=product, quantity=Decimal("1.000"))

    client = APIClient()
    client.force_authenticate(user=supervisor)
    first = client.post(
        "/api/reportes/alertas/",
        {"sync": True, "low_stock_threshold": 2, "cash_diff_threshold": 999},
        format="json",
    )
    second = client.post(
        "/api/reportes/alertas/",
        {"sync": True, "low_stock_threshold": 2, "cash_diff_threshold": 999},
        format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.data["alert_ids"]) == 1
    assert len(second.data["alert_ids"]) == 0

    list_resp = client.get("/api/reportes/alertas/")
    assert list_resp.status_code == 200
    low_stock = [row for row in list_resp.data["results"] if row["alert_type"] == "LOW_STOCK"]
    assert len(low_stock) == 1
    assert low_stock[0]["occurrence_count"] == 2


@pytest.mark.django_db
def test_supervisor_can_resolve_alert_and_view_summary(supervisor):
    bar = Bar.objects.create(name="Bar Resolve")
    location = InventoryLocation.objects.create(
        name="Inventario Bar Resolve",
        location_type=InventoryLocation.LocationType.BAR,
        bar=bar,
    )
    product = Product.objects.create(
        name="Ron Resolve",
        sku="RON-RESOLVE-001",
        unit=Product.Unit.UNIT,
        sale_price=Decimal("8.00"),
        cost_price=Decimal("2.50"),
    )
    InventoryStock.objects.create(location=location, product=product, quantity=Decimal("0.000"))

    client = APIClient()
    client.force_authenticate(user=supervisor)
    scan_resp = client.post(
        "/api/reportes/alertas/",
        {"sync": True, "low_stock_threshold": 1, "cash_diff_threshold": 999},
        format="json",
    )
    assert scan_resp.status_code == 200
    alert_id = scan_resp.data["alert_ids"][0]

    resolve_resp = client.post(f"/api/reportes/alertas/{alert_id}/resolve/", {}, format="json")
    assert resolve_resp.status_code == 200
    assert resolve_resp.data["status"] == "RESOLVED"

    summary_resp = client.get("/api/reportes/alertas/resumen/")
    assert summary_resp.status_code == 200
    payload = summary_resp.data
    assert payload["summary"]["total"] >= 1
    assert payload["summary"]["resolved_total"] >= 1
    assert "dedup" in payload
    assert payload["dedup"]["raw_occurrences"] >= payload["dedup"]["stored_rows"]


@pytest.mark.django_db
def test_cajero_cannot_access_snapshots_and_alerts(cajero):
    client = APIClient()
    client.force_authenticate(user=cajero)

    snapshots_resp = client.get("/api/reportes/snapshots/")
    assert snapshots_resp.status_code == 403

    alerts_resp = client.get("/api/reportes/alertas/")
    assert alerts_resp.status_code == 403

    summary_resp = client.get("/api/reportes/alertas/resumen/")
    assert summary_resp.status_code == 403


@pytest.mark.django_db
def test_alerts_list_supports_pagination_and_ordering(supervisor):
    for i in range(5):
        AlertEvent.objects.create(
            alert_type=AlertEvent.AlertType.LOW_STOCK,
            severity=AlertEvent.Severity.MEDIUM,
            message=f"A{i}",
            payload={"n": i},
        )

    client = APIClient()
    client.force_authenticate(user=supervisor)
    resp = client.get("/api/reportes/alertas/?order_by=id&limit=2&offset=1")
    assert resp.status_code == 200
    assert resp.data["count"] == 2
    assert resp.data["limit"] == 2
    assert resp.data["offset"] == 1
    ids = [row["id"] for row in resp.data["results"]]
    assert ids == sorted(ids)

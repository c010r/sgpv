import pytest
from rest_framework.test import APIRequestFactory

from core.throttles import AlertsScanThrottle, ReportsReadThrottle, SalesCreateThrottle
from reports.views import AlertEventsReportView
from sales.views import SaleViewSet


@pytest.mark.django_db
def test_sale_create_action_has_specific_throttle():
    throttle_classes = SaleViewSet.create_sale.kwargs.get("throttle_classes", [])
    assert SalesCreateThrottle in throttle_classes


@pytest.mark.django_db
def test_alert_events_view_uses_alert_scan_throttle_for_post():
    factory = APIRequestFactory()
    view = AlertEventsReportView()
    view.request = factory.post("/api/reportes/alertas/", {}, format="json")
    throttles = view.get_throttles()
    assert len(throttles) == 1
    assert isinstance(throttles[0], AlertsScanThrottle)


@pytest.mark.django_db
def test_alert_events_view_uses_reports_read_throttle_for_get():
    factory = APIRequestFactory()
    view = AlertEventsReportView()
    view.request = factory.get("/api/reportes/alertas/")
    throttles = view.get_throttles()
    assert len(throttles) == 1
    assert isinstance(throttles[0], ReportsReadThrottle)

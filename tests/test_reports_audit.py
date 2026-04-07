import pytest
from rest_framework.test import APIClient

from core.models import AuditLog


@pytest.mark.django_db
def test_report_access_is_audited_for_supervisor(supervisor):
    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get("/api/reportes/dashboard/")
    assert response.status_code == 200

    audit = AuditLog.objects.filter(action="REPORT_ACCESS", object_id="/api/reportes/dashboard/").first()
    assert audit is not None
    assert audit.actor_id == supervisor.id
    assert audit.metadata["method"] == "GET"
    assert audit.metadata["status_code"] == 200


@pytest.mark.django_db
def test_report_access_is_audited_for_forbidden_user(cajero):
    client = APIClient()
    client.force_authenticate(user=cajero)
    response = client.get("/api/reportes/dashboard/")
    assert response.status_code == 403

    audit = AuditLog.objects.filter(action="REPORT_ACCESS", object_id="/api/reportes/dashboard/").first()
    assert audit is not None
    assert audit.actor_id == cajero.id
    assert audit.metadata["status_code"] == 403

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_healthcheck_is_public_and_ok():
    client = APIClient()
    response = client.get("/healthz/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert "database" in data

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_system_configuration_rejects_invalid_timezone(supervisor):
    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.post(
        "/api/configuracion/",
        {
            "country_code": "UY",
            "currency_code": "USD",
            "timezone": "Invalid/Timezone",
            "costing_method": "AVG",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "timezone" in response.data


@pytest.mark.django_db
def test_system_configuration_normalizes_country_and_currency(supervisor):
    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.post(
        "/api/configuracion/",
        {
            "country_code": " uy ",
            "currency_code": " usd ",
            "timezone": "America/Montevideo",
            "costing_method": "FIFO",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["country_code"] == "UY"
    assert response.data["currency_code"] == "USD"
    assert response.data["costing_method"] == "FIFO"


@pytest.mark.django_db
def test_bar_rejects_blank_name(supervisor):
    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.post("/api/barras/", {"name": "   ", "is_active": True}, format="json")
    assert response.status_code == 400
    assert "name" in response.data

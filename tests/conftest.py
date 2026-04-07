import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def supervisor(db):
    User = get_user_model()
    user = User.objects.create_user(username="sup_test", password="sup123", role="SUPERVISOR")
    return user


@pytest.fixture
def cajero(db):
    User = get_user_model()
    user = User.objects.create_user(username="caj_test", password="caj123", role="CAJERO")
    return user

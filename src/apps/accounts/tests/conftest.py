import pytest
from apps.accounts.models.user import CustomUser


@pytest.fixture
def user_data():
    return {
        "username": "test_user",
        "email": "test@example.com",
        "password": "StrongPass123",
    }
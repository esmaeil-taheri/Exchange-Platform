import pytest

from apps.accounts.services.user_services import UserService
from apps.accounts.selectors.user_selectors import UserSelector


@pytest.mark.django_db
def test_get_user_by_email(user_data):
    user = UserService.register_user(**user_data)
    found_user = UserSelector.get_user_by_email(user.email)

    assert found_user.id == user.id


@pytest.mark.django_db
def test_get_user_by_id(user_data):
    user = UserService.register_user(**user_data)
    found_user = UserSelector.get_user_by_id(user.id)

    assert found_user.email == user.email

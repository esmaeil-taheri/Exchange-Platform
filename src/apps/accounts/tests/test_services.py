from unittest.mock import patch

import pytest

from apps.accounts.services.user_services import UserService
from apps.accounts.models import CustomUser
from apps.accounts.exceptions.user_exceptions import UsernameAlreadyExists


@pytest.mark.django_db
def test_register_user_success(user_data):
    user = UserService.register_user(**user_data)

    assert user.id is not None
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.check_password(user_data["password"])


@pytest.mark.django_db
def test_register_user_username_exists(user_data):
    UserService.register_user(**user_data)

    with pytest.raises(UsernameAlreadyExists):
        UserService.register_user(**user_data)


# @pytest.mark.django_db
# @patch("apps.accounts.signals.user_signals.send_mail")
# def test_register_signal_triggers_email(mock_send_mail, user_data):
#     UserService.register_user(**user_data)

#     assert mock_send_mail.called
#     args, kwargs = mock_send_mail.call_args

#     assert user_data.username in kwargs

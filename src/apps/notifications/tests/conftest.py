import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.user import CustomUser
from apps.notifications.models.notif_template import NotificationTemplate
from apps.notifications.models.notification import Notification
from apps.notifications.models.notif_status import UserNotificationStatus

# ── Shared constants ──────────────────────────────────────────────────────────
PHONE_NUMBER    = '09121111111'
TEMPLATE_CODE   = 'TEST_NOTIF'
TEMPLATE_TITLE  = 'Test Notification'
TEMPLATE_BODY   = 'Hello {{name}}, your balance is {{amount}}.'
TEMPLATE_CATEGORY = 'general'


# ── Fixtures: User ────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A registered user. The post_save signal auto-creates a Customer + Kyc."""
    return CustomUser.objects.create(
        username=f'user-{PHONE_NUMBER}',
        phone_number=PHONE_NUMBER,
        last_ip_address='127.0.0.1',
    )


# ── Fixtures: Template ────────────────────────────────────────────────────────

@pytest.fixture
def template(db):
    """A notification template with two body placeholders."""
    return NotificationTemplate.objects.create(
        code=TEMPLATE_CODE,
        title=TEMPLATE_TITLE,
        body=TEMPLATE_BODY,
        category=TEMPLATE_CATEGORY,
        severity=2,
    )


# ── Fixtures: Notification ────────────────────────────────────────────────────

@pytest.fixture
def notification(user, template, db):
    """An unread user notification with a linked UserNotificationStatus."""
    notif = Notification.objects.create(
        user=user,
        template=template,
        type='user',
        title=template.title,
        body='Hello Ali, your balance is 500000.',
        category=template.category,
        severity=template.severity,
    )
    UserNotificationStatus.objects.create(
        user=user,
        notification=notif,
        is_read=False,
    )
    return notif


# ── Fixtures: HTTP Client ─────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient authenticated with a JWT token for the test user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client

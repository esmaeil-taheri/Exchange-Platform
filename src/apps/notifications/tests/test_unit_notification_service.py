"""
Unit Tests — NotificationService
──────────────────────────────────
DB is used for all tests (service logic is tightly coupled to ORM).
No external services to mock.
"""

import pytest

from apps.notifications.services.notification_services import NotificationService
from apps.notifications.models.notification import Notification
from apps.notifications.models.notif_status import UserNotificationStatus
from apps.notifications.exceptions.notification_exceptions import (
    NotificationNotFound,
    NotificationAlreadyRead,
)

from .conftest import TEMPLATE_CODE, TEMPLATE_TITLE, TEMPLATE_BODY, TEMPLATE_CATEGORY


# ═════════════════════════════════════════════════════════════════════════════
# create_notification_from_template
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreateNotificationFromTemplate:

    def test_missing_template_raises_does_not_exist(self, user):
        from apps.notifications.models.notif_template import NotificationTemplate
        with pytest.raises(NotificationTemplate.DoesNotExist):
            NotificationService.create_notification_from_template(
                template_code='NONEXISTENT_CODE',
                user=user,
            )

    def test_notification_created_with_correct_fields(self, user, template):
        notif = NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=user,
            context={'name': 'Ali', 'amount': '500000'},
        )
        assert notif.pk is not None
        assert notif.title == TEMPLATE_TITLE
        assert notif.category == TEMPLATE_CATEGORY
        assert notif.severity == template.severity
        assert notif.user == user

    def test_context_variables_replaced_in_body(self, user, template):
        notif = NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=user,
            context={'name': 'Reza', 'amount': '1000'},
        )
        assert 'Reza' in notif.body
        assert '1000' in notif.body
        assert '{{name}}' not in notif.body
        assert '{{amount}}' not in notif.body

    def test_user_notification_creates_status_record(self, user, template):
        notif = NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=user,
            context={'name': 'Ali', 'amount': '0'},
        )
        assert notif.type == 'user'
        status = UserNotificationStatus.objects.filter(
            user=user, notification=notif
        ).first()
        assert status is not None
        assert status.is_read is False

    def test_public_notification_has_no_status_record(self, template):
        """When user=None the notification is public and no status row is created."""
        notif = NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=None,
            context={'name': 'all', 'amount': '0'},
        )
        assert notif.type == 'public'
        assert notif.user is None
        assert UserNotificationStatus.objects.filter(notification=notif).count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# mark_as_read
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestMarkAsRead:

    def test_status_not_found_raises_notification_not_found(self, user):
        with pytest.raises(NotificationNotFound):
            NotificationService.mark_as_read(notif_id=99999, user_id=user.id)

    def test_already_read_raises_notification_already_read(self, user, notification):
        # mark it read first
        status = UserNotificationStatus.objects.get(
            user=user, notification=notification
        )
        status.is_read = True
        status.save()

        with pytest.raises(NotificationAlreadyRead):
            NotificationService.mark_as_read(
                notif_id=notification.id, user_id=user.id
            )

    def test_success_sets_is_read_and_read_at(self, user, notification):
        result = NotificationService.mark_as_read(
            notif_id=notification.id, user_id=user.id
        )
        assert result is True

        status = UserNotificationStatus.objects.get(
            user=user, notification=notification
        )
        assert status.is_read is True
        assert status.read_at is not None

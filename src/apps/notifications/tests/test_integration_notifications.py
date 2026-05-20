"""
Integration Tests — notifications
───────────────────────────────────
Real DB and real transactions.
Verifies that service calls produce the correct persistent state.
"""

import pytest

from apps.notifications.services.notification_services import NotificationService
from apps.notifications.models.notification import Notification
from apps.notifications.models.notif_status import UserNotificationStatus

from .conftest import TEMPLATE_CODE


# ═════════════════════════════════════════════════════════════════════════════
# Notification Creation
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNotificationCreationIntegration:

    def test_notification_and_status_both_persisted(self, user, template):
        """A single service call must persist both Notification and UserNotificationStatus."""
        assert Notification.objects.count() == 0
        assert UserNotificationStatus.objects.count() == 0

        NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=user,
            context={'name': 'Ali', 'amount': '200000'},
        )

        assert Notification.objects.count() == 1
        assert UserNotificationStatus.objects.count() == 1

    def test_body_rendered_correctly_in_db(self, user, template):
        """Rendered body (after variable substitution) is what gets saved to DB."""
        NotificationService.create_notification_from_template(
            template_code=TEMPLATE_CODE,
            user=user,
            context={'name': 'Sara', 'amount': '99999'},
        )

        saved = Notification.objects.get(user=user)
        assert 'Sara' in saved.body
        assert '99999' in saved.body


# ═════════════════════════════════════════════════════════════════════════════
# Mark as Read
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestMarkAsReadIntegration:

    def test_is_read_and_read_at_updated_in_db(self, user, notification):
        """mark_as_read must persist is_read=True and a non-null read_at to the DB."""
        NotificationService.mark_as_read(
            notif_id=notification.id,
            user_id=user.id,
        )

        status = UserNotificationStatus.objects.get(
            user=user, notification=notification
        )
        assert status.is_read is True
        assert status.read_at is not None

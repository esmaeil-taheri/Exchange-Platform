"""
API Tests — notifications
──────────────────────────
Full request-to-response cycle.
"""

import pytest

from apps.notifications.models.notif_status import UserNotificationStatus

from .conftest import TEMPLATE_CODE


# ═════════════════════════════════════════════════════════════════════════════
# List Notifications — GET /api/v1/notifications/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetNotificationsListApi:

    URL = '/api/v1/notifications/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_authenticated_with_no_notifications_returns_empty_list(self, auth_client):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_authenticated_with_notification_returns_list(
        self, auth_client, notification
    ):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['title'] == notification.title

    def test_read_notifications_excluded_from_list(
        self, auth_client, user, notification
    ):
        """Notifications already marked as read must not appear in the list."""
        status = UserNotificationStatus.objects.get(
            user=user, notification=notification
        )
        status.is_read = True
        status.save()

        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.data['count'] == 0


# ═════════════════════════════════════════════════════════════════════════════
# Mark as Read — GET /api/v1/notifications/read/<notif_id>/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestReadNotificationApi:

    def _url(self, notif_id):
        return f'/api/v1/notifications/read/{notif_id}/'

    def test_unauthenticated_returns_401(self, api_client, notification):
        response = api_client.get(self._url(notification.id))
        assert response.status_code == 401

    def test_invalid_notif_id_returns_404(self, auth_client):
        response = auth_client.get(self._url(99999))
        assert response.status_code == 404

    def test_valid_notif_id_returns_204(self, auth_client, notification):
        response = auth_client.get(self._url(notification.id))
        assert response.status_code == 204

    def test_reading_twice_returns_403(self, auth_client, notification):
        """
        NotificationAlreadyRead is mapped to 403 in the custom exception handler.
        A second read attempt on the same notification must return 403.
        """
        auth_client.get(self._url(notification.id))
        response = auth_client.get(self._url(notification.id))
        assert response.status_code == 403

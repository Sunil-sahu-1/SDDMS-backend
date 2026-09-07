from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Notification


class NotificationAPITestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="notification_user",
            password="TestPassword123!",
            role=User.Role.NORMAL_USER,
            is_active=True,
        )

        self.other_user = User.objects.create_user(
            username="other_notification_user",
            password="TestPassword123!",
            role=User.Role.NORMAL_USER,
            is_active=True,
        )

        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Test Notification",
            message="This is a test notification.",
            notification_type=Notification.NotificationType.INFO,
        )

        self.read_notification = Notification.objects.create(
            recipient=self.user,
            title="Read Notification",
            message="This notification is already read.",
            notification_type=Notification.NotificationType.SUCCESS,
            is_read=True,
        )

        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            title="Other User Notification",
            message="This belongs to another user.",
            notification_type=Notification.NotificationType.ALERT,
        )

    def authenticate(self, user=None):
        if user is None:
            user = self.user

        self.client.force_authenticate(user=user)

    def test_authenticated_user_can_list_own_notifications(self):
        self.authenticate()

        url = reverse("notification-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

        titles = [
            notification["title"]
            for notification in response.data
        ]

        self.assertIn(
            "Test Notification",
            titles,
        )

        self.assertIn(
            "Read Notification",
            titles,
        )

        self.assertNotIn(
            "Other User Notification",
            titles,
        )

    def test_authenticated_user_can_list_unread_notifications(self):
        self.authenticate()

        url = reverse("notification-unread")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["title"],
            "Test Notification",
        )

    def test_user_can_mark_own_notification_as_read(self):
        self.authenticate()

        url = reverse(
            "notification-read",
            kwargs={
                "pk": self.notification.pk,
            },
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.notification.refresh_from_db()

        self.assertTrue(
            self.notification.is_read
        )

        self.assertIsNotNone(
            self.notification.read_at
        )

        self.assertTrue(
            response.data["is_read"]
        )

        self.assertIsNotNone(
            response.data["read_at"]
        )

    def test_user_cannot_access_other_users_notification(self):
        self.authenticate()

        url = reverse(
            "notification-read",
            kwargs={
                "pk": self.other_notification.pk,
            },
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.other_notification.refresh_from_db()

        self.assertFalse(
            self.other_notification.is_read
        )

    def test_user_can_mark_all_own_notifications_as_read(self):
        self.authenticate()

        url = reverse(
            "notification-read-all"
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["updated_count"],
            1,
        )

        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user,
                is_read=False,
            ).count(),
            0,
        )

        self.other_notification.refresh_from_db()

        self.assertFalse(
            self.other_notification.is_read
        )

    def test_unauthenticated_user_cannot_list_notifications(self):
        url = reverse("notification-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_mark_notification_read(self):
        url = reverse(
            "notification-read",
            kwargs={
                "pk": self.notification.pk,
            },
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.notification.refresh_from_db()

        self.assertFalse(
            self.notification.is_read
        )

    def test_read_notification_remains_read(self):
        self.authenticate()

        url = reverse(
            "notification-read",
            kwargs={
                "pk": self.read_notification.pk,
            },
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.read_notification.refresh_from_db()

        self.assertTrue(
            self.read_notification.is_read
        )
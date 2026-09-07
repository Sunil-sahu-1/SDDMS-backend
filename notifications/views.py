from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer
from .services import (
    get_unread_notification_count,
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


class NotificationListView(APIView):
    """
    Return notifications belonging to the logged-in user.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        notifications = get_user_notifications(
            request.user
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class UnreadNotificationListView(APIView):
    """
    Return unread notifications belonging to
    the logged-in user.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        notifications = get_user_notifications(
            request.user
        ).filter(
            is_read=False,
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class UnreadNotificationCountView(APIView):
    """
    Return unread notification count.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        count = get_unread_notification_count(
            request.user
        )

        return Response(
            {
                "unread_count": count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(APIView):
    """
    Mark one notification as read.

    A user can only access their own notification.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        notification = mark_notification_as_read(
            notification
        )

        serializer = NotificationSerializer(
            notification,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadView(APIView):
    """
    Mark all unread notifications of the
    logged-in user as read.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(self, request):
        updated_count = mark_all_notifications_as_read(
            request.user
        )

        return Response(
            {
                "message": (
                    "All notifications marked as read."
                ),
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )

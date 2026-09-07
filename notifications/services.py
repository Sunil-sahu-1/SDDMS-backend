from django.utils import timezone

from .models import Notification


def create_notification(
    recipient,
    title,
    message,
    notification_type=Notification.NotificationType.INFO,
):
    """
    Create a notification for a specific user.

    Parameters:
        recipient:
            User instance who should receive the notification.

        title:
            Short notification title.

        message:
            Full notification message.

        notification_type:
            Notification type such as INFO, SUCCESS,
            WARNING, ALERT, or SYSTEM.

    Returns:
        Notification instance.
    """

    if recipient is None:
        raise ValueError(
            "Notification recipient cannot be None."
        )

    if not title:
        raise ValueError(
            "Notification title cannot be empty."
        )

    if not message:
        raise ValueError(
            "Notification message cannot be empty."
        )

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def mark_notification_as_read(notification):
    """
    Mark a notification as read.
    """

    if notification is None:
        raise ValueError(
            "Notification cannot be None."
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()

        notification.save(
            update_fields=[
                "is_read",
                "read_at",
            ]
        )

    return notification


def mark_all_notifications_as_read(user):
    """
    Mark all unread notifications of a user as read.
    """

    if user is None:
        raise ValueError(
            "User cannot be None."
        )

    now = timezone.now()

    updated_count = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).update(
        is_read=True,
        read_at=now,
    )

    return updated_count


def get_unread_notification_count(user):
    """
    Return the number of unread notifications
    belonging to a user.
    """

    if user is None:
        raise ValueError(
            "User cannot be None."
        )

    return Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()


def get_user_notifications(user):
    """
    Return all notifications belonging to a user.

    Notifications are returned in the model's default
    ordering: newest first.
    """

    if user is None:
        raise ValueError(
            "User cannot be None."
        )

    return Notification.objects.filter(
        recipient=user,
    )

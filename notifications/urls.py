from django.urls import path

from .views import (
    NotificationListView,
    UnreadNotificationListView,
    UnreadNotificationCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)


urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "unread/",
        UnreadNotificationListView.as_view(),
        name="notification-unread",
    ),
    path(
        "unread-count/",
        UnreadNotificationCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path(
        "read-all/",
        NotificationMarkAllReadView.as_view(),
        name="notification-read-all",
    ),
]

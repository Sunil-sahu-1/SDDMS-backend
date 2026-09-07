from django.urls import path

from .views import AdminDashboardView


urlpatterns = [
    path(
        "",
        AdminDashboardView.as_view(),
        name="admin-dashboard",
    ),
]

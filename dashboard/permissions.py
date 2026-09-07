from rest_framework.permissions import BasePermission


class IsAdminUserRole(BasePermission):
    message = "Only administrators can access the dashboard."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )

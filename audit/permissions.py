from rest_framework.permissions import BasePermission


class IsAdminOrAuthorizedStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        return user.role in [
            "ADMIN",
            "POLICE_OFFICER",
            "INVESTIGATOR",
            "LEGAL_OFFICER",
        ]

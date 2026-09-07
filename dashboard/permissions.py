from rest_framework.permissions import BasePermission


class IsAdminUserRole(BasePermission):
    message = "Only administrators can access the dashboard."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "ADMIN"
        )


class IsStaffDashboardUser(BasePermission):
    message = "Only verified operational staff can access this dashboard."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        if user.role == "ADMIN":
            return True

        if user.role not in {
            "POLICE_OFFICER",
            "INVESTIGATOR",
            "LEGAL_OFFICER",
        }:
            return False

        try:
            return user.verification.status == "VERIFIED"
        except Exception:
            return False

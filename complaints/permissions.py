from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.models import User, UserVerification


class ComplaintAccessPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        action = getattr(view, "action", None)

        if user.role == User.Role.ADMIN:
            return True

        if user.role == User.Role.NORMAL_USER:
            return action in ["list", "retrieve", "create"]

        if user.role in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]:
            return self._is_verified(user)

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        action = getattr(view, "action", None)

        if user.role == User.Role.ADMIN:
            return True

        if user.role == User.Role.NORMAL_USER:
            return (
                obj.complainant_id == user.id
                and action in ["list", "retrieve"]
                and request.method in SAFE_METHODS
            )

        if user.role in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
        ]:
            return action in ["list", "retrieve", "update_status", "convert_to_case"]

        if user.role == User.Role.LEGAL_OFFICER:
            return (
                action in ["list", "retrieve"]
                and request.method in SAFE_METHODS
            )

        return False

    def _is_verified(self, user):
        verification = getattr(user, "verification", None)
        return (
            verification is not None
            and verification.status == UserVerification.Status.VERIFIED
        )

from rest_framework.permissions import BasePermission

from accounts.models import User, UserVerification


class CaseAccessPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        role = user.role
        action = getattr(view, "action", None)

        if role == User.Role.ADMIN:
            return True

        if role == User.Role.NORMAL_USER:
            return action == "create" and request.method == "POST"

        if role == User.Role.POLICE_OFFICER:
            if not self._is_verified_staff(user):
                return False

            return action in [
                "list",
                "retrieve",
                "create",
                "case_history",
                "update_status",
                "partial_update",
            ]

        if role == User.Role.INVESTIGATOR:
            if not self._is_verified_staff(user):
                return False

            return action in [
                "list",
                "retrieve",
                "case_history",
                "update_status",
                "partial_update",
            ]

        if role == User.Role.LEGAL_OFFICER:
            if not self._is_verified_staff(user):
                return False

            return action in [
                "list",
                "retrieve",
                "case_history",
            ]

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        role = user.role
        action = getattr(view, "action", None)

        if role == User.Role.ADMIN:
            return True

        if role == User.Role.NORMAL_USER:
            return (
                obj.complainant_id == user.id
                and action in ["retrieve", "case_history"]
                and request.method in ["GET", "HEAD", "OPTIONS"]
            )

        if role == User.Role.POLICE_OFFICER:
            if not self._is_verified_staff(user):
                return False

            if obj.assigned_officer_id != user.id:
                return False

            if action in ["retrieve", "case_history"]:
                return request.method in ["GET", "HEAD", "OPTIONS"]

            if action == "update_status":
                return request.method == "POST"

            # Police officers may update assignment fields on cases
            # they are currently assigned to.
            if action == "partial_update":
                return request.method == "PATCH"

            return False

        if role == User.Role.INVESTIGATOR:
            if not self._is_verified_staff(user):
                return False

            if obj.assigned_investigator_id != user.id:
                return False

            if action in ["retrieve", "case_history"]:
                return request.method in ["GET", "HEAD", "OPTIONS"]

            if action == "update_status":
                return request.method == "POST"

            # Investigators may update assignment fields on cases
            # they are currently assigned to.
            if action == "partial_update":
                return request.method == "PATCH"

            return False

        if role == User.Role.LEGAL_OFFICER:
            if not self._is_verified_staff(user):
                return False

            return (
                action in ["retrieve", "case_history"]
                and request.method in ["GET", "HEAD", "OPTIONS"]
            )

        return False

    def _is_verified_staff(self, user):
        """Check whether a staff user has been verified."""
        if user.role == User.Role.ADMIN:
            return True

        if user.role not in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]:
            return False

        try:
            verification = user.verification
        except UserVerification.DoesNotExist:
            return False

        return verification.status == UserVerification.Status.VERIFIED

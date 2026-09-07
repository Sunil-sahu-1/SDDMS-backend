
from rest_framework.permissions import BasePermission

from accounts.models import User, UserVerification


class CaseAccessPermission(BasePermission):
    
    def has_permission(self, request, view):
        user = request.user

        # Authentication check
        if not user or not user.is_authenticated:
            return False

        # Active user check
        if not user.is_active:
            return False

        role = user.role
        action = getattr(view, "action", None)

        # ==========================================================
        # ADMIN
        # ==========================================================
        if role == User.Role.ADMIN:
            return True

        # ==========================================================
        # NORMAL USER
        # ==========================================================
        if role == User.Role.NORMAL_USER:
            return (
                action == "create"
                and request.method == "POST"
            )

        # ==========================================================
        # POLICE OFFICER
        # ==========================================================
        if role == User.Role.POLICE_OFFICER:

            # Police Officer must be verified.
            if not self._is_verified_staff(user):
                return False

            return action in [
                "list",
                "retrieve",
                "create",
                "case_history",
                "update_status",
            ]

        # ==========================================================
        # INVESTIGATOR
        # ==========================================================
        if role == User.Role.INVESTIGATOR:

            if not self._is_verified_staff(user):
                return False

            return action in [
                "list",
                "retrieve",
                "case_history",
                "update_status",
            ]

        # ==========================================================
        # LEGAL OFFICER
        # ==========================================================
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

        # Authentication check
        if not user or not user.is_authenticated:
            return False

        # Active user check
        if not user.is_active:
            return False

        role = user.role
        action = getattr(view, "action", None)

        # ==========================================================
        # ADMIN
        # ==========================================================
        if role == User.Role.ADMIN:
            return True

        # ==========================================================
        # NORMAL USER
        # ==========================================================
        if role == User.Role.NORMAL_USER:
            return (
                obj.complainant_id == user.id
                and action in [
                    "retrieve",
                    "case_history",
                ]
                and request.method in [
                    "GET",
                    "HEAD",
                    "OPTIONS",
                ]
            )

        # ==========================================================
        # POLICE OFFICER
        # ==========================================================
        if role == User.Role.POLICE_OFFICER:

            if not self._is_verified_staff(user):
                return False

            # Police Officer can access only assigned cases.
            if obj.assigned_officer_id != user.id:
                return False

            # View case / history
            if action in [
                "retrieve",
                "case_history",
            ]:
                return request.method in [
                    "GET",
                    "HEAD",
                    "OPTIONS",
                ]

            # Update case status
            if action == "update_status":
                return request.method == "POST"

            return False

        # ==========================================================
        # INVESTIGATOR
        # ==========================================================
        if role == User.Role.INVESTIGATOR:

            if not self._is_verified_staff(user):
                return False

            # Investigator can access only assigned cases.
            if obj.assigned_investigator_id != user.id:
                return False

            # View case / history
            if action in [
                "retrieve",
                "case_history",
            ]:
                return request.method in [
                    "GET",
                    "HEAD",
                    "OPTIONS",
                ]

            # Update case status
            if action == "update_status":
                return request.method == "POST"

            return False

        # ==========================================================
        # LEGAL OFFICER
        # ==========================================================
        if role == User.Role.LEGAL_OFFICER:

            if not self._is_verified_staff(user):
                return False

            return (
                action in [
                    "retrieve",
                    "case_history",
                ]
                and request.method in [
                    "GET",
                    "HEAD",
                    "OPTIONS",
                ]
            )

        return False

    def _is_verified_staff(self, user):
        """
        Check whether a Police Officer, Investigator,
        or Legal Officer has been verified.
        """

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

        return (
            verification.status
            == UserVerification.Status.VERIFIED
        )

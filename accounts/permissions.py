from rest_framework.permissions import BasePermission

from .models import User, UserVerification


class IsVerifiedUser(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        if user.role == User.Role.ADMIN:
            return True

        verification = getattr(
            user,
            "verification",
            None,
        )

        if verification is None:
            return False

        return (
            verification.status
            == UserVerification.Status.VERIFIED
        )


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.ADMIN
        )


class IsPoliceOfficer(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.POLICE_OFFICER
            and IsVerifiedUser().has_permission(
                request,
                view,
            )
        )


class IsInvestigator(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.INVESTIGATOR
            and IsVerifiedUser().has_permission(
                request,
                view,
            )
        )


class IsLegalOfficer(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.LEGAL_OFFICER
            and IsVerifiedUser().has_permission(
                request,
                view,
            )
        )


class IsNormalUser(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.NORMAL_USER
            and IsVerifiedUser().has_permission(
                request,
                view,
            )
        )


class IsStaffOrAdmin(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.is_active
            and user.role in [
                User.Role.ADMIN,
                User.Role.POLICE_OFFICER,
                User.Role.INVESTIGATOR,
                User.Role.LEGAL_OFFICER,
            ]
            and IsVerifiedUser().has_permission(
                request,
                view,
            )
        )


class HasRole(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return False

        if not IsVerifiedUser().has_permission(
            request,
            view,
        ):
            return False

        allowed_roles = getattr(
            view,
            "allowed_roles",
            [],
        )

        return user.role in allowed_roles

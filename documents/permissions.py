from django.utils import timezone
from rest_framework.permissions import BasePermission

from accounts.models import User
from accounts.permissions import IsVerifiedUser

from .models import DocumentShare


class DocumentAccessPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return False

        # Normal users have NO document access.
        if user.role == User.Role.NORMAL_USER:
            return False

        # Admin has access, subject to object-level
        # archive rules.
        if user.role == User.Role.ADMIN:
            return True

        # All other users must be verified.
        return IsVerifiedUser().has_permission(
            request,
            view,
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return False

        # Normal users cannot access documents at all.
        if user.role == User.Role.NORMAL_USER:
            return False

        # Archived documents are not accessible.
        if obj.is_archived:
            return False

        # Admin has full access to non-archived documents.
        if user.role == User.Role.ADMIN:
            return True

        # User must be verified.
        if not IsVerifiedUser().has_permission(
            request,
            view,
        ):
            return False

        # Police Officer:
        # only documents belonging to assigned cases.
        if user.role == User.Role.POLICE_OFFICER:
            if (
                obj.case
                and obj.case.assigned_officer_id == user.id
            ):
                return True

        # Investigator:
        # only documents belonging to assigned cases.
        elif user.role == User.Role.INVESTIGATOR:
            if (
                obj.case
                and obj.case.assigned_investigator_id == user.id
            ):
                return True

        # Legal Officer:
        # access through an active, non-expired share.
        elif user.role == User.Role.LEGAL_OFFICER:
            share = (
                DocumentShare.objects
                .filter(
                    document=obj,
                    shared_with=user,
                    is_active=True,
                )
                .first()
            )

            if share:
                if (
                    share.expires_at is None
                    or share.expires_at > timezone.now()
                ):
                    return True

        # Check explicit document sharing for other
        # verified staff as well.
        share = (
            DocumentShare.objects
            .filter(
                document=obj,
                shared_with=user,
                is_active=True,
            )
            .first()
        )

        if share:
            if (
                share.expires_at is None
                or share.expires_at > timezone.now()
            ):
                return True

        return False
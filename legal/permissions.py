from rest_framework.permissions import BasePermission


class LegalAccessPermission(BasePermission):
    """
    Legal module access.

    ADMIN:
        Full access.

    LEGAL_OFFICER:
        Apne assigned legal records/cases par access.

    Other roles:
        No access.
    """

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            "ADMIN",
            "LEGAL_OFFICER",
        ]

    def has_object_permission(
        self,
        request,
        view,
        obj
    ):

        user = request.user

        if user.role == "ADMIN":
            return True

        if user.role != "LEGAL_OFFICER":
            return False

        # LegalReview / CourtHearing dono mein
        # case aur legal_officer available hain.
        return obj.legal_officer_id == user.id

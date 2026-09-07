from rest_framework.permissions import BasePermission


ALLOWED_ROLES = [
    "ADMIN",
    "POLICE_OFFICER",
    "INVESTIGATOR",
]


class EvidenceAccessPermission(
    BasePermission
):

    def has_permission(
        self,
        request,
        view
    ):

        if not (
            request.user
            and request.user.is_authenticated
        ):
            return False

        return request.user.role in ALLOWED_ROLES

    def has_object_permission(
        self,
        request,
        view,
        obj
    ):

        user = request.user

        if user.role == "ADMIN":
            return True

        if (
            user.role == "POLICE_OFFICER"
            and obj.case.assigned_officer_id
            == user.id
        ):
            return True

        if (
            user.role == "INVESTIGATOR"
            and obj.case.assigned_investigator_id
            == user.id
        ):
            return True

        # Current custodian gets access
        if (
            obj.current_custodian_id
            == user.id
        ):
            return True

        return False


class WitnessStatementPermission(
    BasePermission
):

    def has_permission(
        self,
        request,
        view
    ):

        if not (
            request.user
            and request.user.is_authenticated
        ):
            return False

        return request.user.role in ALLOWED_ROLES

    def has_object_permission(
        self,
        request,
        view,
        obj
    ):

        user = request.user

        if user.role == "ADMIN":
            return True

        if (
            user.role == "POLICE_OFFICER"
            and obj.case.assigned_officer_id
            == user.id
        ):
            return True

        if (
            user.role == "INVESTIGATOR"
            and obj.case.assigned_investigator_id
            == user.id
        ):
            return True

        return False

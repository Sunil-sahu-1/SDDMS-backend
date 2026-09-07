from rest_framework.permissions import BasePermission


class InvestigationPermission(BasePermission):
    allowed_roles = {
        "ADMIN",
        "INVESTIGATOR",
        "POLICE_OFFICER",
    }

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if getattr(user, "role", None) not in self.allowed_roles:
            return False

        if request.method == "POST":
            return getattr(user, "role", None) in {
                "ADMIN",
                "INVESTIGATOR",
            }

        if request.method == "DELETE":
            return getattr(user, "role", None) == "ADMIN"

        if getattr(view, "action", None) in {
            "assign",
            "status",
        }:
            return getattr(user, "role", None) in {
                "ADMIN",
                "INVESTIGATOR",
            }

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role", None)

        if role == "ADMIN":
            return True

        if role == "INVESTIGATOR":
            if obj.lead_investigator_id == user.id:
                return True

            if obj.assigned_officers.filter(id=user.id).exists():
                return True

            return obj.case.assigned_investigator_id == user.id

        if role == "POLICE_OFFICER":
            if obj.assigned_officers.filter(id=user.id).exists():
                return True

            return obj.case.assigned_officer_id == user.id

        return False


class WitnessStatementPermission(BasePermission):
    allowed_roles = {
        "ADMIN",
        "POLICE_OFFICER",
        "LEGAL_OFFICER",
    }

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", None)

        if role not in self.allowed_roles:
            return False

        if request.method == "POST":
            return role in {
                "ADMIN",
                "POLICE_OFFICER",
                "LEGAL_OFFICER",
            }

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role", None)

        if role == "ADMIN":
            return True

        if role == "POLICE_OFFICER":
            return (
                obj.case.assigned_officer_id == user.id
                or obj.recorded_by_id == user.id
            )

        if role == "LEGAL_OFFICER":
            return obj.recorded_by_id == user.id

        return False
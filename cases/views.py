from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import Case, CaseHistory
from .serializers import CaseSerializer, CaseHistorySerializer
from .permissions import CaseAccessPermission


class CaseViewSet(viewsets.ModelViewSet):
    serializer_class = CaseSerializer
    permission_classes = [CaseAccessPermission]

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated or not user.is_active:
            return Case.objects.none()

        queryset = (
            Case.objects
            .select_related(
                "complainant",
                "assigned_officer",
                "assigned_investigator",
                "assigned_legal_officer",
                "created_by",
            )
            .prefetch_related("history__changed_by")
            .order_by("-created_at")
        )

        if user.role == "ADMIN":
            return queryset

        if user.role == "NORMAL_USER":
            return queryset.filter(complainant=user)

        # Verified police officers and investigators need to see the
        # assignable case register. The object permission layer controls
        # what they can change: only assignment fields/status actions.
        if user.role in ["POLICE_OFFICER", "INVESTIGATOR"]:
            if self.permission_classes[0]()._is_verified_staff(user):
                return queryset
            return Case.objects.none()

        if user.role == "LEGAL_OFFICER":
            return queryset.filter(assigned_legal_officer=user)

        return Case.objects.none()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            {
                "success": True,
                "message": "Case created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        case = serializer.save(
            complainant=self.request.user,
            created_by=self.request.user,
        )

        CaseHistory.objects.create(
            case=case,
            changed_by=self.request.user,
            old_status="",
            new_status=case.status,
            comment="Case created.",
        )

        create_audit_log(
            request=self.request,
            action="CREATE",
            case=case,
            description="Case created.",
            metadata={
                "case_number": case.case_number,
                "status": case.status,
            },
        )

    def update(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": "Only administrators can update cases.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """Update a case or, for verified staff, only its assignments."""
        role = request.user.role

        if role == "ADMIN":
            return super().partial_update(request, *args, **kwargs)

        if role not in ["POLICE_OFFICER", "INVESTIGATOR"]:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators, police officers, and "
                        "investigators can change case assignments."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_fields = {
            "assigned_officer",
            "assigned_investigator",
        }
        submitted_fields = set(request.data.keys())
        invalid_fields = submitted_fields - allowed_fields

        if invalid_fields:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Police officers and investigators may update "
                        "only assigned officer and assigned investigator."
                    ),
                    "invalid_fields": sorted(invalid_fields),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        case = self.get_object()
        User = get_user_model()

        for field in allowed_fields.intersection(submitted_fields):
            raw_value = request.data.get(field)

            if raw_value in [None, "", "null"]:
                continue

            try:
                selected_user = User.objects.get(
                    id=raw_value,
                    is_active=True,
                )
            except (User.DoesNotExist, ValueError, TypeError):
                return Response(
                    {
                        "success": False,
                        "message": f"Selected {field.replace('_', ' ')} was not found.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            expected_role = (
                "POLICE_OFFICER"
                if field == "assigned_officer"
                else "INVESTIGATOR"
            )

            if selected_user.role != expected_role:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Selected user must have the {expected_role} role."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                verification = selected_user.verification
            except Exception:
                verification = None

            if (
                verification is None
                or verification.status != "VERIFIED"
            ):
                return Response(
                    {
                        "success": False,
                        "message": "Selected staff member is not verified.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        old_officer = case.assigned_officer_id
        old_investigator = case.assigned_investigator_id

        serializer = self.get_serializer(
            case,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        case.refresh_from_db()

        changed = []
        if old_officer != case.assigned_officer_id:
            changed.append(
                f"assigned officer to {case.assigned_officer.get_full_name() or case.assigned_officer.username if case.assigned_officer else 'none'}"
            )
        if old_investigator != case.assigned_investigator_id:
            changed.append(
                f"assigned investigator to {case.assigned_investigator.get_full_name() or case.assigned_investigator.username if case.assigned_investigator else 'none'}"
            )

        if changed:
            comment = "Case assignment updated: " + ", ".join(changed) + "."
            CaseHistory.objects.create(
                case=case,
                changed_by=request.user,
                old_status=case.status,
                new_status=case.status,
                comment=comment,
            )

            create_audit_log(
                request=request,
                action="ASSIGN",
                case=case,
                description="Case personnel assignment updated.",
                metadata={
                    "case_number": case.case_number,
                    "assigned_officer": case.assigned_officer_id,
                    "assigned_investigator": case.assigned_investigator_id,
                },
            )

        return Response(
            {
                "success": True,
                "message": "Case assignment updated successfully.",
                "data": self.get_serializer(case).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="history")
    def case_history(self, request, pk=None):
        case = self.get_object()
        serializer = CaseHistorySerializer(
            case.history.select_related("changed_by").all(),
            many=True,
        )
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="update-status")
    @transaction.atomic
    def update_status(self, request, pk=None):
        case = self.get_object()
        new_status = request.data.get("status")
        comment = str(request.data.get("comment", "")).strip()

        valid_statuses = {choice[0] for choice in Case.Status.choices}
        if new_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "message": "Invalid case status.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = case.status
        case.status = new_status
        case.save(update_fields=["status", "updated_at"])

        CaseHistory.objects.create(
            case=case,
            changed_by=request.user,
            old_status=old_status,
            new_status=new_status,
            comment=comment,
        )

        create_audit_log(
            request=request,
            action="UPDATE",
            case=case,
            description="Case status updated.",
            metadata={
                "case_number": case.case_number,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Case status updated successfully.",
                "data": self.get_serializer(case).data,
            },
            status=status.HTTP_200_OK,
        )

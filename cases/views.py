from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import Case, CaseHistory
from .serializers import (
    CaseSerializer,
    CaseHistorySerializer,
)
from .permissions import CaseAccessPermission


class CaseViewSet(viewsets.ModelViewSet):

    serializer_class = CaseSerializer

    permission_classes = [
        CaseAccessPermission,
    ]

    def get_queryset(self):

        user = self.request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
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
            .prefetch_related(
                "history__changed_by",
            )
            .order_by("-created_at")
        )

        if user.role == "ADMIN":
            return queryset

        if user.role == "NORMAL_USER":
            return queryset.filter(
                complainant=user,
            )

        if user.role == "POLICE_OFFICER":
            return queryset.filter(
                assigned_officer=user,
            )

        if user.role == "INVESTIGATOR":
            return queryset.filter(
                assigned_investigator=user,
            )

        if user.role == "LEGAL_OFFICER":
            return queryset.filter(
                assigned_legal_officer=user,
            )

        return Case.objects.none()

    @transaction.atomic
    def create(
        self,
        request,
        *args,
        **kwargs,
    ):

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        self.perform_create(serializer)

        headers = self.get_success_headers(
            serializer.data,
        )

        return Response(
            {
                "success": True,
                "message": "Case created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(
        self,
        serializer,
    ):

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

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):

        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators can "
                        "update cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(
            request,
            *args,
            **kwargs,
        )

    def partial_update(
        self,
        request,
        *args,
        **kwargs,
    ):

        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators can "
                        "update cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):

        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators can "
                        "delete cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        case = self.get_object()

        create_audit_log(
            request=request,
            action="DELETE",
            case=case,
            description="Case deleted.",
            metadata={
                "case_number": case.case_number,
            },
        )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-legal",
    )
    @transaction.atomic
    def assign_legal(
        self,
        request,
        pk=None,
    ):

        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators can "
                        "assign cases to legal officers."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        case = self.get_object()

        legal_officer_id = request.data.get(
            "legal_officer",
        )

        if not legal_officer_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Legal officer ID is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            legal_officer = User.objects.get(
                id=legal_officer_id,
                is_active=True,
            )
        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Legal officer not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if legal_officer.role != "LEGAL_OFFICER":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Selected user is not a legal officer."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_officer = (
            case.assigned_legal_officer
        )

        case.assigned_legal_officer = legal_officer

        case.save(
            update_fields=[
                "assigned_legal_officer",
                "updated_at",
            ],
        )

        CaseHistory.objects.create(
            case=case,
            changed_by=request.user,
            old_status=case.status,
            new_status=case.status,
            comment=(
                f"Case transferred to legal officer "
                f"{legal_officer.get_full_name() or legal_officer.username}."
            ),
        )

        create_audit_log(
            request=request,
            action="ASSIGN",
            case=case,
            description=(
                "Case assigned to legal officer."
            ),
            metadata={
                "case_number": case.case_number,
                "previous_legal_officer": (
                    previous_officer.id
                    if previous_officer
                    else None
                ),
                "legal_officer": legal_officer.id,
                "legal_officer_name": (
                    legal_officer.get_full_name()
                    or legal_officer.username
                ),
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Case assigned to legal officer "
                    "successfully."
                ),
                "data": CaseSerializer(
                    case,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="remove-legal",
    )
    @transaction.atomic
    def remove_legal(
        self,
        request,
        pk=None,
    ):

        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only administrators can "
                        "remove legal assignment."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        case = self.get_object()

        previous_officer = (
            case.assigned_legal_officer
        )

        if not previous_officer:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No legal officer is assigned "
                        "to this case."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        case.assigned_legal_officer = None

        case.save(
            update_fields=[
                "assigned_legal_officer",
                "updated_at",
            ],
        )

        CaseHistory.objects.create(
            case=case,
            changed_by=request.user,
            old_status=case.status,
            new_status=case.status,
            comment=(
                f"Legal assignment removed from "
                f"{previous_officer.get_full_name() or previous_officer.username}."
            ),
        )

        create_audit_log(
            request=request,
            action="UNASSIGN",
            case=case,
            description=(
                "Legal officer assignment removed."
            ),
            metadata={
                "case_number": case.case_number,
                "previous_legal_officer": (
                    previous_officer.id
                ),
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Legal officer assignment "
                    "removed successfully."
                ),
                "data": CaseSerializer(
                    case,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="update-status",
    )
    @transaction.atomic
    def update_status(
        self,
        request,
        pk=None,
    ):

        case = self.get_object()

        new_status = request.data.get(
            "status",
        )

        comment = request.data.get(
            "comment",
            "",
        )

        valid_statuses = {
            value
            for value, label in Case.Status.choices
        }

        if new_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "message": "Invalid case status.",
                    "valid_statuses": list(
                        valid_statuses
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = case.status

        if old_status == new_status:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Case already has "
                        "this status."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        case.status = new_status

        case.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

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
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Case status updated "
                    "successfully."
                ),
                "data": CaseSerializer(
                    case,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="history",
    )
    def case_history(
        self,
        request,
        pk=None,
    ):

        case = self.get_object()

        history = case.history.all()

        create_audit_log(
            request=request,
            action="VIEW",
            case=case,
            description="Case history viewed.",
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Case history retrieved "
                    "successfully."
                ),
                "data": CaseHistorySerializer(
                    history,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )
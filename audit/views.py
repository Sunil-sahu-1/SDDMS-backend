from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import AuditLog
from .permissions import IsAdminOrAuthorizedStaff
from .serializers import (
    AuditLogSerializer,
    AuditIntegritySerializer,
)
from .utils import verify_audit_chain


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    permission_classes = [
        IsAuthenticated,
        IsAdminOrAuthorizedStaff,
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            AuditLog.objects
            .select_related(
                "user",
                "case",
                "document",
            )
            .order_by("-created_at")
        )

        if user.role == "ADMIN":
            return queryset

        if user.role == "POLICE_OFFICER":
            return queryset.filter(
                case__assigned_officer=user
            )

        if user.role == "INVESTIGATOR":
            return queryset.filter(
                case__assigned_investigator=user
            )

        if user.role == "LEGAL_OFFICER":
            return queryset.filter(
                case__legal_officer=user
            )

        return queryset.none()

    @action(
        detail=False,
        methods=["get"],
        url_path="verify-integrity",
    )
    def verify_integrity(self, request):
        if request.user.role != "ADMIN":
            return Response(
                {
                    "success": False,
                    "message": "Only administrators can verify the audit chain.",
                    "data": None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        result = verify_audit_chain()

        serializer = AuditIntegritySerializer(result)

        return Response(
            {
                "success": result["valid"],
                "message": result["message"],
                "data": serializer.data,
            },
            status=(
                status.HTTP_200_OK
                if result["valid"]
                else status.HTTP_409_CONFLICT
            ),
        )

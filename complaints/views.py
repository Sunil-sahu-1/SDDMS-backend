import uuid

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User, UserVerification
from audit.utils import create_audit_log
from cases.models import Case, CaseHistory

from .models import Complaint
from .permissions import ComplaintAccessPermission
from .serializers import ComplaintSerializer


class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    permission_classes = [ComplaintAccessPermission]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.is_active:
            return Complaint.objects.none()

        queryset = (
            Complaint.objects
            .select_related("complainant", "case")
            .order_by("-created_at")
        )

        if user.role == User.Role.ADMIN:
            return queryset
        if user.role == User.Role.NORMAL_USER:
            return queryset.filter(complainant=user)
        if user.role in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]:
            return queryset
        return queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.NORMAL_USER:
            return Response(
                {"success": False, "message": "Only normal users can submit complaints."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        complaint = serializer.save(
            complainant=self.request.user,
            complaint_number="CMP-" + uuid.uuid4().hex[:10].upper(),
        )
        create_audit_log(
            request=self.request,
            action="CREATE",
            description="Complaint submitted.",
            metadata={
                "complaint_id": complaint.id,
                "complaint_number": complaint.complaint_number,
                "status": complaint.status,
            },
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"success": False, "message": "Complaint updates are not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"success": False, "message": "Complaint updates are not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"success": False, "message": "Complaint deletion is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="update-status")
    @transaction.atomic
    def update_status(self, request, pk=None):
        if request.user.role not in [
            User.Role.ADMIN,
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
        ]:
            return Response(
                {"success": False, "message": "You are not authorized to update complaint status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        complaint = self.get_object()
        new_status = request.data.get("status")
        comment = str(request.data.get("comment", "")).strip()

        valid_statuses = {value for value, _ in Complaint.Status.choices}
        if new_status not in valid_statuses:
            return Response(
                {"success": False, "message": "Invalid complaint status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == Complaint.Status.CONVERTED_TO_CASE:
            return Response(
                {"success": False, "message": "Use the convert-to-case action to convert an accepted complaint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if complaint.status == new_status:
            return Response(
                {"success": False, "message": "Complaint already has this status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = complaint.status
        complaint.status = new_status
        complaint.save(update_fields=["status", "updated_at"])

        create_audit_log(
            request=request,
            action="UPDATE",
            description="Complaint status updated.",
            metadata={
                "complaint_id": complaint.id,
                "complaint_number": complaint.complaint_number,
                "old_status": old_status,
                "new_status": new_status,
                "comment": comment,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Complaint status updated successfully.",
                "data": ComplaintSerializer(
                    complaint,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="convert-to-case")
    @transaction.atomic
    def convert_to_case(self, request, pk=None):
        user = request.user

        if user.role not in [
            User.Role.ADMIN,
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
        ]:
            return Response(
                {"success": False, "message": "You are not authorized to convert complaints into cases."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.role != User.Role.ADMIN:
            verification = getattr(user, "verification", None)
            if (
                verification is None
                or verification.status != UserVerification.Status.VERIFIED
            ):
                return Response(
                    {"success": False, "message": "Only verified staff can convert complaints into cases."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        complaint = self.get_object()

        if complaint.case_id is not None:
            return Response(
                {
                    "success": False,
                    "message": "This complaint has already been converted into a case.",
                    "case_id": complaint.case_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if complaint.status != Complaint.Status.ACCEPTED:
            return Response(
                {
                    "success": False,
                    "message": "Only accepted complaints can be converted into cases.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        case_number = "CASE-" + uuid.uuid4().hex[:10].upper()
        while Case.objects.filter(case_number=case_number).exists():
            case_number = "CASE-" + uuid.uuid4().hex[:10].upper()

        assigned_officer = None
        assigned_investigator = None
        if user.role == User.Role.POLICE_OFFICER:
            assigned_officer = user
        elif user.role == User.Role.INVESTIGATOR:
            assigned_investigator = user

        case = Case.objects.create(
            case_number=case_number,
            title=complaint.subject,
            description=complaint.description,
            complainant=complaint.complainant,
            created_by=user,
            assigned_officer=assigned_officer,
            assigned_investigator=assigned_investigator,
            status=Case.Status.OPEN,
        )

        CaseHistory.objects.create(
            case=case,
            changed_by=user,
            old_status="",
            new_status=case.status,
            comment=f"Case created from complaint {complaint.complaint_number}.",
        )

        complaint.case = case
        complaint.status = Complaint.Status.CONVERTED_TO_CASE
        complaint.save(update_fields=["case", "status", "updated_at"])

        create_audit_log(
            request=request,
            action="UPDATE",
            case=case,
            description="Complaint converted into case.",
            metadata={
                "complaint_id": complaint.id,
                "complaint_number": complaint.complaint_number,
                "case_id": case.id,
                "case_number": case.case_number,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Complaint converted into case successfully.",
                "data": {
                    "complaint": ComplaintSerializer(
                        complaint,
                        context={"request": request},
                    ).data,
                    "case": {
                        "id": case.id,
                        "case_number": case.case_number,
                        "title": case.title,
                        "status": case.status,
                    },
                },
            },
            status=status.HTTP_201_CREATED,
        )

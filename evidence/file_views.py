from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from audit.utils import create_audit_log

from .models import Evidence


def _has_evidence_access(request, evidence):
    user = request.user

    if not user.is_authenticated or not user.is_active:
        return False
    if evidence.is_archived:
        return False
    if user.role == "ADMIN":
        return True

    if user.role == "POLICE_OFFICER":
        return bool(
            evidence.case_id
            and evidence.case.assigned_officer_id == user.id
        ) or evidence.current_custodian_id == user.id

    if user.role == "INVESTIGATOR":
        return bool(
            evidence.case_id
            and evidence.case.assigned_investigator_id == user.id
        ) or evidence.current_custodian_id == user.id

    return False


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_evidence(request, pk):
    evidence = get_object_or_404(
        Evidence.objects.select_related("case"),
        pk=pk,
    )

    if not _has_evidence_access(request, evidence):
        return Response(
            {"success": False, "message": "You do not have permission to view this evidence."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not evidence.file:
        return Response(
            {"success": False, "message": "Evidence file not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    create_audit_log(
        request=request,
        action="VIEW",
        case=evidence.case,
        description="Evidence viewed.",
        metadata={
            "evidence_id": evidence.id,
            "evidence_number": evidence.evidence_number,
        },
    )

    response = FileResponse(
        evidence.file.open("rb"),
        as_attachment=False,
    )
    response["Content-Type"] = evidence.mime_type or "application/octet-stream"
    response["Content-Disposition"] = (
        f'inline; filename="{evidence.original_filename}"'
    )
    return response

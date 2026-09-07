from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from audit.utils import create_audit_log

from .models import Document, DocumentShare


def _has_document_access(request, document):
    user = request.user

    if not user.is_authenticated or not user.is_active:
        return False
    if document.is_archived:
        return False
    if user.role == "ADMIN" or user.role == "NORMAL_USER":
        return user.role == "ADMIN"

    if user.role == "POLICE_OFFICER" and document.case_id:
        if document.case.assigned_officer_id == user.id:
            return True

    if user.role == "INVESTIGATOR" and document.case_id:
        if document.case.assigned_investigator_id == user.id:
            return True

    share = DocumentShare.objects.filter(
        document=document,
        shared_with=user,
        is_active=True,
    ).first()

    return bool(
        share
        and (
            share.expires_at is None
            or share.expires_at > timezone.now()
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_document(request, pk):
    document = get_object_or_404(
        Document.objects.select_related("case"),
        pk=pk,
    )

    if not _has_document_access(request, document):
        return Response(
            {"success": False, "message": "You do not have permission to view this document."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not document.file:
        return Response(
            {"success": False, "message": "Document file not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    create_audit_log(
        request=request,
        action="VIEW",
        case=document.case,
        document=document,
        description="Document viewed.",
        metadata={"version": document.version},
    )

    response = FileResponse(
        document.file.open("rb"),
        as_attachment=False,
    )
    response["Content-Type"] = document.mime_type or "application/octet-stream"
    response["Content-Disposition"] = (
        f'inline; filename="{document.original_filename}"'
    )
    return response

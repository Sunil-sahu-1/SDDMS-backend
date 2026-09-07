import hashlib
import uuid

from django.db import transaction
from django.http import FileResponse

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import (
    Evidence,
    EvidenceActivity,
    EvidenceCustodyTransfer,
)
from .permissions import EvidenceAccessPermission
from .serializers import (
    EvidenceActivitySerializer,
    EvidenceCustodySerializer,
    EvidenceSerializer,
    EvidenceTransferSerializer,
)


class EvidenceViewSet(viewsets.ModelViewSet):

    serializer_class = EvidenceSerializer

    permission_classes = [
        EvidenceAccessPermission
    ]

    def get_queryset(self):

        user = self.request.user

        if not user.is_authenticated:
            return Evidence.objects.none()

        queryset = (
            Evidence.objects
            .select_related(
                "case",
                "collected_by",
                "current_custodian",
            )
            .prefetch_related(
                "custody_transfers",
                "activities",
            )
        )

        if user.role == "ADMIN":
            return queryset.filter(
                is_archived=False
            )

        if user.role == "POLICE_OFFICER":
            return queryset.filter(
                is_archived=False
            ).filter(
                case__assigned_officer=user
            ) | queryset.filter(
                is_archived=False,
                current_custodian=user,
            )

        if user.role == "INVESTIGATOR":
            return queryset.filter(
                is_archived=False
            ).filter(
                case__assigned_investigator=user
            ) | queryset.filter(
                is_archived=False,
                current_custodian=user,
            )

        return Evidence.objects.none()

    def perform_create(self, serializer):

        uploaded_file = self.request.FILES.get(
            "file"
        )

        if not uploaded_file:
            raise serializers.ValidationError(
                {
                    "file": (
                        "Evidence file is required."
                    )
                }
            )

        sha256 = hashlib.sha256()

        for chunk in uploaded_file.chunks():
            sha256.update(chunk)

        uploaded_file.seek(0)

        evidence_number = (
            "EVD-"
            + uuid.uuid4().hex[:10].upper()
        )

        evidence = serializer.save(
            evidence_number=evidence_number,
            collected_by=self.request.user,
            current_custodian=self.request.user,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=getattr(
                uploaded_file,
                "content_type",
                ""
            ),
            sha256_hash=sha256.hexdigest()
        )

        # Initial custody record
        EvidenceCustodyTransfer.objects.create(
            evidence=evidence,
            from_user=None,
            to_user=self.request.user,
            transferred_by=self.request.user,
            transfer_type=(
                EvidenceCustodyTransfer
                .TransferType.INITIAL
            ),
            reason="Initial evidence collection.",
            location="",
            sha256_hash=evidence.sha256_hash,
        )

        EvidenceActivity.objects.create(
            evidence=evidence,
            actor=self.request.user,
            action=EvidenceActivity.Action.UPLOAD,
            description="Evidence uploaded.",
            metadata={
                "evidence_number": (
                    evidence.evidence_number
                ),
                "sha256": evidence.sha256_hash,
            },
        )

        create_audit_log(
            request=self.request,
            action="UPLOAD",
            case=evidence.case,
            description="Evidence uploaded.",
            metadata={
                "evidence_id": evidence.id,
                "evidence_number": (
                    evidence.evidence_number
                ),
                "sha256": evidence.sha256_hash,
                "current_custodian": (
                    self.request.user.id
                ),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="transfer"
    )
    @transaction.atomic
    def transfer(self, request, pk=None):

        evidence = self.get_object()

        if evidence.is_archived:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Archived evidence "
                        "cannot be transferred."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EvidenceTransferSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        to_user_id = serializer.validated_data[
            "to_user"
        ]

        reason = serializer.validated_data.get(
            "reason",
            ""
        )

        location = serializer.validated_data.get(
            "location",
            ""
        )

        transfer_type = serializer.validated_data[
            "transfer_type"
        ]

        # Prevent transfer to same custodian
        if (
            evidence.current_custodian_id
            == to_user_id
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Evidence is already "
                        "in this user's custody."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only admin or current custodian can transfer
        if (
            request.user.role != "ADMIN"
            and evidence.current_custodian_id
            != request.user.id
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only the current custodian "
                        "or an admin can transfer "
                        "this evidence."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate target user
        target_user = (
            self._get_valid_custodian(
                to_user_id
            )
        )

        if not target_user:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Target user must be an "
                        "active police officer, "
                        "investigator, or admin."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify current file integrity before transfer
        current_hash = self._calculate_hash(
            evidence
        )

        if current_hash != evidence.sha256_hash:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Evidence integrity "
                        "verification failed. "
                        "Transfer blocked."
                    ),
                    "stored_sha256": (
                        evidence.sha256_hash
                    ),
                    "current_sha256": current_hash,
                },
                status=status.HTTP_409_CONFLICT
            )

        previous_custodian = (
            evidence.current_custodian
        )

        EvidenceCustodyTransfer.objects.create(
            evidence=evidence,
            from_user=previous_custodian,
            to_user=target_user,
            transferred_by=request.user,
            transfer_type=transfer_type,
            reason=reason,
            location=location,
            sha256_hash=current_hash,
        )

        evidence.current_custodian = target_user
        evidence.save(
            update_fields=[
                "current_custodian",
                "updated_at",
            ]
        )

        EvidenceActivity.objects.create(
            evidence=evidence,
            actor=request.user,
            action=EvidenceActivity.Action.TRANSFER,
            description=(
                "Evidence custody transferred."
            ),
            metadata={
                "from_user": (
                    previous_custodian.id
                    if previous_custodian
                    else None
                ),
                "to_user": target_user.id,
                "reason": reason,
                "location": location,
                "sha256": current_hash,
            },
        )

        create_audit_log(
            request=request,
            action="TRANSFER",
            case=evidence.case,
            description=(
                "Evidence custody transferred."
            ),
            metadata={
                "evidence_id": evidence.id,
                "from_user": (
                    previous_custodian.id
                    if previous_custodian
                    else None
                ),
                "to_user": target_user.id,
                "reason": reason,
                "location": location,
                "sha256": current_hash,
            }
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Evidence transferred "
                    "successfully."
                ),
                "evidence_id": evidence.id,
                "evidence_number": (
                    evidence.evidence_number
                ),
                "previous_custodian": (
                    previous_custodian.id
                    if previous_custodian
                    else None
                ),
                "current_custodian": (
                    target_user.id
                ),
                "sha256_hash": current_hash,
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="custody-history"
    )
    def custody_history(
        self,
        request,
        pk=None
    ):

        evidence = self.get_object()

        history = (
            EvidenceCustodyTransfer.objects
            .filter(evidence=evidence)
            .select_related(
                "from_user",
                "to_user",
                "transferred_by",
            )
            .order_by("-transferred_at")
        )

        return Response(
            {
                "success": True,
                "evidence_id": evidence.id,
                "evidence_number": (
                    evidence.evidence_number
                ),
                "current_custodian": (
                    evidence.current_custodian_id
                ),
                "history": (
                    EvidenceCustodySerializer(
                        history,
                        many=True,
                        context={
                            "request": request
                        },
                    ).data
                ),
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="activity"
    )
    def activity(
        self,
        request,
        pk=None
    ):

        evidence = self.get_object()

        activities = (
            EvidenceActivity.objects
            .filter(evidence=evidence)
            .select_related("actor")
            .order_by("-created_at")
        )

        return Response(
            {
                "success": True,
                "evidence_id": evidence.id,
                "evidence_number": (
                    evidence.evidence_number
                ),
                "activities": (
                    EvidenceActivitySerializer(
                        activities,
                        many=True,
                        context={
                            "request": request
                        },
                    ).data
                ),
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="download"
    )
    def download(self, request, pk=None):

        evidence = self.get_object()

        if evidence.is_archived:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Evidence is archived."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        EvidenceActivity.objects.create(
            evidence=evidence,
            actor=request.user,
            action=EvidenceActivity.Action.DOWNLOAD,
            description="Evidence downloaded.",
            metadata={
                "evidence_number": (
                    evidence.evidence_number
                ),
            },
        )

        create_audit_log(
            request=request,
            action="DOWNLOAD",
            case=evidence.case,
            description="Evidence downloaded.",
            metadata={
                "evidence_id": evidence.id,
                "evidence_number": (
                    evidence.evidence_number
                ),
            }
        )

        return FileResponse(
            evidence.file.open("rb"),
            as_attachment=True,
            filename=evidence.original_filename
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="verify-integrity"
    )
    def verify_integrity(
        self,
        request,
        pk=None
    ):

        evidence = self.get_object()

        current_hash = self._calculate_hash(
            evidence
        )

        is_valid = (
            current_hash
            == evidence.sha256_hash
        )

        EvidenceActivity.objects.create(
            evidence=evidence,
            actor=request.user,
            action=EvidenceActivity.Action.VERIFY,
            description=(
                "Evidence integrity verified."
            ),
            metadata={
                "stored_sha256": (
                    evidence.sha256_hash
                ),
                "current_sha256": current_hash,
                "integrity_valid": is_valid,
            },
        )

        create_audit_log(
            request=request,
            action="VERIFY",
            case=evidence.case,
            description=(
                "Evidence integrity verified."
            ),
            metadata={
                "evidence_id": evidence.id,
                "stored_sha256": (
                    evidence.sha256_hash
                ),
                "current_sha256": current_hash,
                "integrity_valid": is_valid,
            }
        )

        return Response(
            {
                "success": True,
                "evidence_id": evidence.id,
                "stored_sha256": (
                    evidence.sha256_hash
                ),
                "current_sha256": current_hash,
                "integrity_valid": is_valid,
            }
        )

    def _calculate_hash(self, evidence):

        sha256 = hashlib.sha256()

        with evidence.file.open("rb") as file:
            for chunk in iter(
                lambda: file.read(
                    1024 * 1024
                ),
                b""
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _get_valid_custodian(
        self,
        user_id
    ):

        from django.contrib.auth import (
            get_user_model
        )

        User = get_user_model()

        return (
            User.objects.filter(
                id=user_id,
                is_active=True,
                role__in=[
                    "ADMIN",
                    "POLICE_OFFICER",
                    "INVESTIGATOR",
                ],
            )
            .first()
        )

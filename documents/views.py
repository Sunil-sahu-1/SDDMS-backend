from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from django.conf import settings

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import (
    Document,
    DocumentVersion,
    DocumentShare,
    DocumentSignature,
)

from .serializers import (
    DocumentSerializer,
    DocumentVersionSerializer,
    DocumentShareSerializer,
    DocumentSignatureSerializer,
)

from .permissions import DocumentAccessPermission


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [DocumentAccessPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated or not user.is_active:
            return Document.objects.none()

        now = timezone.now()

        if user.role == "ADMIN":
            return (
                Document.objects
                .filter(is_archived=False)
                .select_related("case", "uploaded_by")
                .distinct()
            )

        if user.role == "NORMAL_USER":
            return (
                Document.objects
                .filter(
                    case__complainant=user,
                    is_archived=False,
                )
                .select_related("case", "uploaded_by")
                .distinct()
            )

        if user.role == "POLICE_OFFICER":
            return (
                Document.objects.filter(
                    is_archived=False,
                    case__assigned_officer=user,
                )
                | Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__isnull=True,
                )
                | Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__gt=now,
                )
            ).select_related(
                "case",
                "uploaded_by",
            ).distinct()

        if user.role == "INVESTIGATOR":
            return (
                Document.objects.filter(
                    is_archived=False,
                    case__assigned_investigator=user,
                )
                | Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__isnull=True,
                )
                | Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__gt=now,
                )
            ).select_related(
                "case",
                "uploaded_by",
            ).distinct()

        if user.role == "LEGAL_OFFICER":
            return (
                Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__isnull=True,
                )
                | Document.objects.filter(
                    is_archived=False,
                    shares__shared_with=user,
                    shares__is_active=True,
                    shares__expires_at__gt=now,
                )
            ).select_related(
                "case",
                "uploaded_by",
            ).distinct()

        return Document.objects.none()

    def create(self, request, *args, **kwargs):
        if request.user.role not in [
            "ADMIN",
            "NORMAL_USER",
            "POLICE_OFFICER",
            "INVESTIGATOR",
        ]:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to upload documents.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get("file")

        if uploaded_file is None:
            uploaded_file = request.data.get("file")

        if not uploaded_file:
            return Response(
                {
                    "success": False,
                    "message": "Document file is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["file"] = uploaded_file

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)

        return Response(
            {
                "success": True,
                "message": "Document uploaded successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")

        if not uploaded_file:
            uploaded_file = self.request.data.get("file")

        if not uploaded_file:
            raise serializers.ValidationError(
                {
                    "file": "Document file is required."
                }
            )

        with transaction.atomic():
            document = serializer.save(
                uploaded_by=self.request.user,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                mime_type=getattr(
                    uploaded_file,
                    "content_type",
                    "",
                ),
            )

            DocumentVersion.objects.create(
                document=document,
                version_number=1,
                file=document.file,
                original_filename=document.original_filename,
                file_size=document.file_size,
                mime_type=document.mime_type,
                sha256_hash=document.sha256_hash,
                uploaded_by=self.request.user,
                change_note="Initial document upload.",
            )

            create_audit_log(
                request=self.request,
                action="UPLOAD",
                case=document.case,
                document=document,
                description="Document uploaded.",
                metadata={
                    "version": 1,
                    "sha256": document.sha256_hash,
                },
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="new-version",
    )
    def new_version(self, request, pk=None):
        document = self.get_object()

        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {
                    "success": False,
                    "message": "Document file is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        next_version = document.version + 1

        with transaction.atomic():
            document.file = uploaded_file
            document.original_filename = uploaded_file.name
            document.file_size = uploaded_file.size
            document.mime_type = getattr(
                uploaded_file,
                "content_type",
                "",
            )
            document.version = next_version
            document.save()

            version = DocumentVersion.objects.create(
                document=document,
                version_number=next_version,
                file=document.file,
                original_filename=document.original_filename,
                file_size=document.file_size,
                mime_type=document.mime_type,
                sha256_hash=document.sha256_hash,
                uploaded_by=request.user,
                change_note=request.data.get(
                    "change_note",
                    "",
                ),
            )

            create_audit_log(
                request=request,
                action="NEW_VERSION",
                case=document.case,
                document=document,
                description="New document version uploaded.",
                metadata={
                    "version": next_version,
                    "sha256": document.sha256_hash,
                },
            )

        return Response(
            {
                "success": True,
                "message": "New document version uploaded successfully.",
                "data": DocumentVersionSerializer(version).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="versions",
    )
    def versions(self, request, pk=None):
        document = self.get_object()

        versions = document.versions.all().order_by(
            "-version_number"
        )

        return Response(
            {
                "success": True,
                "data": DocumentVersionSerializer(
                    versions,
                    many=True,
                ).data,
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="download",
    )
    def download(self, request, pk=None):
        document = self.get_object()

        if not document.file:
            return Response(
                {
                    "success": False,
                    "message": "Document file not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        create_audit_log(
            request=request,
            action="DOWNLOAD",
            case=document.case,
            document=document,
            description="Document downloaded.",
            metadata={
                "version": document.version,
            },
        )

        response = FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.original_filename,
        )

        return response

    @action(
        detail=True,
        methods=["get"],
        url_path="verify-integrity",
    )
    def verify_integrity(self, request, pk=None):
        document = self.get_object()

        if not document.file:
            return Response(
                {
                    "success": False,
                    "message": "Document file not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        document.file.open("rb")

        hasher = hashes.Hash(hashes.SHA256())

        for chunk in document.file.chunks():
            hasher.update(chunk)

        current_hash = hasher.finalize().hex()

        document.file.close()

        valid = current_hash == document.sha256_hash

        return Response(
            {
                "success": True,
                "valid": valid,
                "stored_hash": document.sha256_hash,
                "current_hash": current_hash,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="share",
    )
    def share(self, request, pk=None):
        document = self.get_object()

        serializer = DocumentShareSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        share = serializer.save(
            document=document,
            shared_by=request.user,
        )

        create_audit_log(
            request=request,
            action="SHARE",
            case=document.case,
            document=document,
            description="Document shared with another user.",
            metadata={
                "shared_with": share.shared_with_id,
                "permission": share.permission,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Document shared successfully.",
                "data": DocumentShareSerializer(
                    share
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="shared-with-me",
    )
    def shared_with_me(self, request):
        now = timezone.now()

        shares = (
            DocumentShare.objects
            .filter(
                shared_with=request.user,
                is_active=True,
            )
            .filter(
                serializers.Q(expires_at__isnull=True)
                | serializers.Q(expires_at__gt=now)
            )
            .select_related(
                "document",
                "shared_with",
                "shared_by",
            )
            .order_by("-created_at")
        )

        return Response(
            {
                "success": True,
                "data": DocumentShareSerializer(
                    shares,
                    many=True,
                ).data,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="archive",
    )
    def archive(self, request, pk=None):
        document = self.get_object()

        document.is_archived = True
        document.save(
            update_fields=[
                "is_archived",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="ARCHIVE",
            case=document.case,
            document=document,
            description="Document archived.",
            metadata={
                "version": document.version,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Document archived successfully.",
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="sign",
    )
    def sign(self, request, pk=None):
        document = self.get_object()

        private_key_pem = request.data.get("private_key")

        if not private_key_pem:
            return Response(
                {
                    "success": False,
                    "message": "Private key is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Invalid private key.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            signature = private_key.sign(
                document.sha256_hash.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Document signing failed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        signature_obj = DocumentSignature.objects.create(
            document=document,
            signed_by=request.user,
            version=document.version,
            document_hash=document.sha256_hash,
            signature=base64.b64encode(
                signature
            ).decode(),
            algorithm="RSA-SHA256",
        )

        create_audit_log(
            request=request,
            action="SIGN",
            case=document.case,
            document=document,
            description="Document digitally signed.",
            metadata={
                "version": document.version,
                "signature_id": signature_obj.id,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Document signed successfully.",
                "data": DocumentSignatureSerializer(
                    signature_obj
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="verify-signature",
    )
    def verify_signature(self, request, pk=None):
        document = self.get_object()

        signature_id = request.data.get("signature_id")

        if not signature_id:
            return Response(
                {
                    "success": False,
                    "message": "Signature ID is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            signature_obj = DocumentSignature.objects.get(
                id=signature_id,
                document=document,
            )
        except DocumentSignature.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Signature not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        public_key_pem = request.data.get("public_key")

        if not public_key_pem:
            return Response(
                {
                    "success": False,
                    "message": "Public key is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )

            public_key.verify(
                base64.b64decode(
                    signature_obj.signature
                ),
                signature_obj.document_hash.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

            valid = True

        except (
            InvalidSignature,
            ValueError,
            TypeError,
        ):
            valid = False

        return Response(
            {
                "success": True,
                "valid": valid,
                "signature_id": signature_obj.id,
                "document_hash": signature_obj.document_hash,
                "algorithm": signature_obj.algorithm,
            }
        )
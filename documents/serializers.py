from rest_framework import serializers

from .models import (
    Document,
    DocumentVersion,
    DocumentShare,
    DocumentSignature,
)


class DocumentVersionSerializer(serializers.ModelSerializer):

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True
    )

    class Meta:
        model = DocumentVersion

        fields = [
            "id",
            "document",
            "version_number",
            "file",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "uploaded_by",
            "uploaded_by_username",
            "change_note",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "version_number",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
        ]


class DocumentSignatureSerializer(serializers.ModelSerializer):

    signed_by_username = serializers.CharField(
        source="signed_by.username",
        read_only=True
    )

    class Meta:
        model = DocumentSignature

        fields = [
            "id",
            "document",
            "signed_by",
            "signed_by_username",
            "version",
            "document_hash",
            "signature",
            "algorithm",
            "signed_at",
        ]

        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True
    )

    versions = DocumentVersionSerializer(
        many=True,
        read_only=True
    )

    signatures = DocumentSignatureSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Document

        fields = [
            "id",
            "case",
            "title",
            "document_type",
            "file",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "version",
            "uploaded_by",
            "uploaded_by_username",
            "is_archived",
            "created_at",
            "updated_at",
            "versions",
            "signatures",
        ]

        read_only_fields = [
            "id",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "version",
            "uploaded_by",
            "uploaded_by_username",
            "is_archived",
            "created_at",
            "updated_at",
            "versions",
            "signatures",
        ]

    def validate_file(self, value):

        max_size = 10 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                "File size cannot exceed 10 MB."
            )

        allowed_types = [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        content_type = getattr(
            value,
            "content_type",
            None
        )

        if content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported file type."
            )

        return value


class DocumentShareSerializer(serializers.ModelSerializer):

    shared_with_username = serializers.CharField(
        source="shared_with.username",
        read_only=True
    )

    shared_by_username = serializers.CharField(
        source="shared_by.username",
        read_only=True
    )

    class Meta:
        model = DocumentShare

        fields = [
            "id",
            "document",
            "shared_with",
            "shared_with_username",
            "permission",
            "shared_by",
            "shared_by_username",
            "expires_at",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "shared_by",
            "shared_by_username",
            "created_at",
        ]

    def validate_permission(self, value):

        if value not in [
            "VIEW",
            "DOWNLOAD",
            "EDIT",
        ]:
            raise serializers.ValidationError(
                "Invalid document permission."
            )

        return value

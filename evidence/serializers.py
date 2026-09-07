from rest_framework import serializers

from .models import (
    Evidence,
    EvidenceActivity,
    EvidenceCustodyTransfer,
)


class EvidenceSerializer(
    serializers.ModelSerializer
):

    collected_by_username = serializers.CharField(
        source="collected_by.username",
        read_only=True
    )

    current_custodian_username = serializers.CharField(
        source="current_custodian.username",
        read_only=True
    )

    class Meta:
        model = Evidence

        fields = [
            "id",
            "case",
            "evidence_number",
            "title",
            "description",
            "evidence_type",
            "file",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "collected_by",
            "collected_by_username",
            "current_custodian",
            "current_custodian_username",
            "is_archived",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "evidence_number",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "collected_by",
            "collected_by_username",
            "current_custodian",
            "current_custodian_username",
            "is_archived",
            "created_at",
            "updated_at",
        ]

    def validate_file(self, uploaded_file):

      max_size = 50 * 1024 * 1024

      if uploaded_file.size > max_size:
        raise serializers.ValidationError(
            "Evidence file cannot exceed 50 MB." )

      return uploaded_file



class EvidenceTransferSerializer(
    serializers.Serializer
):

    to_user = serializers.IntegerField()

    reason = serializers.CharField(
        required=False,
        allow_blank=True
    )

    location = serializers.CharField(
        required=False,
        allow_blank=True
    )

    transfer_type = serializers.ChoiceField(
        choices=[
            (
                EvidenceCustodyTransfer
                .TransferType.TRANSFER
            ),
            (
                EvidenceCustodyTransfer
                .TransferType.RETURN
            ),
        ],
        default=EvidenceCustodyTransfer
        .TransferType.TRANSFER
    )


class EvidenceCustodySerializer(
    serializers.ModelSerializer
):

    from_username = serializers.CharField(
        source="from_user.username",
        read_only=True
    )

    to_username = serializers.CharField(
        source="to_user.username",
        read_only=True
    )

    transferred_by_username = serializers.CharField(
        source="transferred_by.username",
        read_only=True
    )

    transfer_type_display = serializers.CharField(
        source="get_transfer_type_display",
        read_only=True
    )

    class Meta:
        model = EvidenceCustodyTransfer

        fields = [
            "id",
            "evidence",
            "from_user",
            "from_username",
            "to_user",
            "to_username",
            "transferred_by",
            "transferred_by_username",
            "transfer_type",
            "transfer_type_display",
            "reason",
            "location",
            "sha256_hash",
            "transferred_at",
            "created_at",
        ]

        read_only_fields = fields


class EvidenceActivitySerializer(
    serializers.ModelSerializer
):

    actor_username = serializers.CharField(
        source="actor.username",
        read_only=True
    )

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True
    )

    class Meta:
        model = EvidenceActivity

        fields = [
            "id",
            "evidence",
            "actor",
            "actor_username",
            "action",
            "action_display",
            "description",
            "metadata",
            "created_at",
        ]

        read_only_fields = fields

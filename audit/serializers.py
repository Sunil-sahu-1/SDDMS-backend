from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    user_id = serializers.IntegerField(
        source="user.id",
        read_only=True,
    )

    user_role = serializers.CharField(
        source="user.role",
        read_only=True,
    )

    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True,
        allow_null=True,
    )

    document_title = serializers.CharField(
        source="document.title",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user_id",
            "username",
            "user_role",
            "action",
            "case",
            "case_number",
            "document",
            "document_title",
            "description",
            "ip_address",
            "user_agent",
            "metadata",
            "previous_hash",
            "record_hash",
            "created_at",
        ]
        read_only_fields = fields


class AuditIntegritySerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    total_records = serializers.IntegerField()
    invalid_records = serializers.ListField()
    message = serializers.CharField()

from rest_framework import serializers
from .models import (
    Investigation,
    InvestigationHistory,
    WitnessStatement,
    WitnessStatementMedia,
)


class InvestigationSerializer(serializers.ModelSerializer):
    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True
    )

    lead_investigator_name = serializers.SerializerMethodField()
    assigned_officers_names = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Investigation
        fields = [
            "id",
            "investigation_number",
            "case",
            "case_number",
            "title",
            "description",
            "lead_investigator",
            "lead_investigator_name",
            "assigned_officers",
            "assigned_officers_names",
            "status",
            "priority",
            "started_at",
            "completed_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_lead_investigator_name(self, obj):
        if not obj.lead_investigator:
            return None
        return (
            obj.lead_investigator.get_full_name()
            or obj.lead_investigator.username
        )

    def get_assigned_officers_names(self, obj):
        return [
            officer.get_full_name() or officer.username
            for officer in obj.assigned_officers.all()
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return (
            obj.created_by.get_full_name()
            or obj.created_by.username
        )


class InvestigationAssignmentSerializer(serializers.Serializer):
    lead_investigator = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    assigned_officers = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )


class InvestigationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Investigation.Status.choices
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True
    )


class InvestigationTimelineSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InvestigationHistory
        fields = [
            "id",
            "old_status",
            "new_status",
            "comment",
            "changed_by",
            "changed_by_name",
            "created_at",
        ]

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None

        return (
            obj.changed_by.get_full_name()
            or obj.changed_by.username
        )


class WitnessStatementMediaSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WitnessStatementMedia
        fields = [
            "id",
            "media_type",
            "file",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]

    def validate(self, attrs):
        file = attrs.get("file")
        media_type = attrs.get("media_type")

        if not file:
            raise serializers.ValidationError({
                "file": "Media file is required."
            })

        content_type = getattr(file, "content_type", "")

        if media_type == WitnessStatementMedia.MediaType.PHOTO:
            allowed_types = {
                "image/jpeg",
                "image/png",
                "image/webp",
            }

            if content_type not in allowed_types:
                raise serializers.ValidationError({
                    "file": "Only JPG, PNG and WEBP photos are allowed."
                })

            if file.size > 10 * 1024 * 1024:
                raise serializers.ValidationError({
                    "file": "Photo cannot exceed 10 MB."
                })

        elif media_type == WitnessStatementMedia.MediaType.VIDEO:
            allowed_types = {
                "video/mp4",
                "video/webm",
                "video/quicktime",
            }

            if content_type not in allowed_types:
                raise serializers.ValidationError({
                    "file": "Only MP4, WEBM and MOV videos are allowed."
                })

            if file.size > 100 * 1024 * 1024:
                raise serializers.ValidationError({
                    "file": "Video cannot exceed 100 MB."
                })

        else:
            raise serializers.ValidationError({
                "media_type": "Media type must be PHOTO or VIDEO."
            })

        return attrs

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return None

        return (
            obj.uploaded_by.get_full_name()
            or obj.uploaded_by.username
        )


class WitnessStatementSerializer(serializers.ModelSerializer):
    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True
    )

    recorded_by_name = serializers.SerializerMethodField()

    media = WitnessStatementMediaSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = WitnessStatement
        fields = [
            "id",
            "statement_number",
            "case",
            "case_number",
            "witness_reference",
            "witness_name",
            "witness_contact",
            "classification",
            "statement",
            "recorded_by",
            "recorded_by_name",
            "statement_date",
            "status",
            "is_archived",
            "media",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "case_number",
            "recorded_by",
            "recorded_by_name",
            "media",
            "created_at",
            "updated_at",
        ]

    def validate_statement_number(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Statement number is required."
            )

        return value

    def validate_witness_reference(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Witness reference is required."
            )

        return value

    def validate_witness_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Witness name must contain at least 2 characters."
            )

        return value

    def validate_statement(self, value):
        value = value.strip()

        if len(value) < 20:
            raise serializers.ValidationError(
                "Statement must contain at least 20 characters."
            )

        return value

    def validate_classification(self, value):
        allowed = {
            WitnessStatement.Classification.CONFIDENTIAL,
            WitnessStatement.Classification.HIGHLY_CONFIDENTIAL,
            WitnessStatement.Classification.RESTRICTED,
        }

        if value not in allowed:
            raise serializers.ValidationError(
                "Invalid classification."
            )

        return value
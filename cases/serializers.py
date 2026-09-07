from rest_framework import serializers

from .models import Case, CaseHistory


class CaseHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = CaseHistory
        fields = [
            "id",
            "changed_by",
            "changed_by_username",
            "old_status",
            "new_status",
            "comment",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "changed_by",
            "changed_by_username",
            "created_at",
        ]


class CaseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    complainant_username = serializers.CharField(
        source="complainant.username",
        read_only=True,
    )

    assigned_officer_username = serializers.CharField(
        source="assigned_officer.username",
        read_only=True,
    )

    assigned_investigator_username = serializers.CharField(
        source="assigned_investigator.username",
        read_only=True,
    )

    assigned_legal_officer_username = serializers.CharField(
        source="assigned_legal_officer.username",
        read_only=True,
    )

    history = CaseHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Case
        fields = [
            "id",
            "case_number",
            "fir_number",
            "title",
            "description",
            "complainant",
            "complainant_username",
            "assigned_officer",
            "assigned_officer_username",
            "assigned_investigator",
            "assigned_investigator_username",
            "assigned_legal_officer",
            "assigned_legal_officer_username",
            "status",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "history",
        ]
        read_only_fields = [
            "id",
            "complainant_username",
            "assigned_officer_username",
            "assigned_investigator_username",
            "assigned_legal_officer_username",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "history",
        ]

    def validate(self, attrs):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "Request context is required."
            )

        if not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        return attrs
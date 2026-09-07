from rest_framework import serializers

from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):

    complainant_username = serializers.CharField(
        source="complainant.username",
        read_only=True,
    )

    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True,
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "complainant",
            "complainant_username",
            "subject",
            "description",
            "status",
            "case",
            "case_number",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "complaint_number",
            "complainant",
            "complainant_username",
            "status",
            "case",
            "case_number",
            "created_at",
            "updated_at",
        ]

    def validate_subject(self, value):
        value = value.strip()

        if len(value) < 5:
            raise serializers.ValidationError(
                "Subject must contain at least 5 characters."
            )

        return value

    def validate_description(self, value):
        value = value.strip()

        if len(value) < 10:
            raise serializers.ValidationError(
                "Description must contain at least 10 characters."
            )

        return value

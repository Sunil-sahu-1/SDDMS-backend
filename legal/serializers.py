from rest_framework import serializers

from .models import LegalReview, CourtHearing


class LegalReviewSerializer(serializers.ModelSerializer):

    legal_officer_username = serializers.CharField(
        source="legal_officer.username",
        read_only=True
    )

    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True
    )

    class Meta:
        model = LegalReview

        fields = [
            "id",
            "case",
            "case_number",
            "legal_officer",
            "legal_officer_username",
            "title",
            "legal_opinion",
            "status",
            "remarks",
            "reviewed_at",
            "is_archived",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "legal_officer",
            "legal_officer_username",
            "case_number",
            "is_archived",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):

        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Legal review title is too short."
            )

        return value

    def validate_legal_opinion(self, value):

        return value.strip()


class CourtHearingSerializer(serializers.ModelSerializer):

    legal_officer_username = serializers.CharField(
        source="legal_officer.username",
        read_only=True
    )

    case_number = serializers.CharField(
        source="case.case_number",
        read_only=True
    )

    class Meta:
        model = CourtHearing

        fields = [
            "id",
            "case",
            "case_number",
            "legal_officer",
            "legal_officer_username",
            "court_name",
            "hearing_date",
            "hearing_purpose",
            "status",
            "outcome",
            "is_archived",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "legal_officer",
            "legal_officer_username",
            "case_number",
            "is_archived",
            "created_at",
            "updated_at",
        ]

    def validate_court_name(self, value):

        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Court name is too short."
            )

        return value

    def validate_hearing_purpose(self, value):

        return value.strip()

    def validate_outcome(self, value):

        return value.strip()

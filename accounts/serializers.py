from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import UserVerification



User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    verification_type = serializers.ChoiceField(
        choices=[
            User.Role.NORMAL_USER,
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]
    )

    proof_number = serializers.CharField(
        write_only=True,
        max_length=100,
    )

    proof_document = serializers.FileField(
        write_only=True,
    )

    photo = serializers.ImageField(
        write_only=True,
    )

    designation = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=150,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "verification_type",
            "proof_number",
            "proof_document",
            "photo",
            "department",
            "designation",
        ]

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Username cannot be empty."
            )

        if User.objects.filter(
            username__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )

        return value

    def validate_email(self, value):
        value = value.strip()

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def validate(self, attrs):
        verification_type = attrs.get(
            "verification_type"
        )

        # ADMIN accounts can never be created
        # through public registration.
        if verification_type == User.Role.ADMIN:
            raise serializers.ValidationError(
                {
                    "verification_type": (
                        "Admin accounts cannot be created "
                        "through public registration."
                    )
                }
            )

        # Staff applicants must provide department
        # and designation.
        if verification_type in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]:
            if not attrs.get("department"):
                raise serializers.ValidationError(
                    {
                        "department": (
                            "Department is required for "
                            "staff applications."
                        )
                    }
                )

            if not attrs.get("designation"):
                raise serializers.ValidationError(
                    {
                        "designation": (
                            "Designation is required for "
                            "staff applications."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop(
            "password"
        )

        verification_type = validated_data.pop(
            "verification_type"
        )

        proof_number = validated_data.pop(
            "proof_number"
        )

        proof_document = validated_data.pop(
            "proof_document"
        )

        photo = validated_data.pop(
            "photo"
        )

        designation = validated_data.pop(
            "designation",
            "",
        )

        department = validated_data.get(
            "department"
        )

        with transaction.atomic():

            user = User(
                **validated_data,
                role=verification_type,
                is_active=True,
            )

            user.set_password(password)
            user.save()

            UserVerification.objects.create(
                user=user,
                verification_type=verification_type,
                proof_number=proof_number,
                proof_document=proof_document,
                photo=photo,
                department=department,
                designation=designation,
                status=UserVerification.Status.PENDING,
            )

        return user

class UserSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "department",
            "role",
            "is_active",
            "verification_status",
            "date_joined",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "role",
            "department",
            "is_active",
            "verification_status",
            "date_joined",
            "created_at",
            "updated_at",
        ]

    def get_verification_status(self, obj):
        verification = getattr(
            obj,
            "verification",
            None,
        )

        if verification is None:
            return "NOT_SUBMITTED"

        return verification.status


class UserVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = [
            "id",
            "verification_type",
            "proof_number",
            "proof_document",
            "photo",
            "department",
            "designation",
            "status",
            "verified_by",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "verified_by",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "Request context is required."
            )

        user = request.user

        if not user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        if user.role == User.Role.ADMIN:
            raise serializers.ValidationError(
                {
                    "verification_type": (
                        "Admin accounts do not require user verification."
                    )
                }
            )

        if hasattr(user, "verification"):
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Verification has already been submitted."
                    )
                }
            )

        verification_type = attrs.get("verification_type")

        if verification_type != user.role:
            raise serializers.ValidationError(
                {
                    "verification_type": (
                        "Verification type must match your current account role."
                    )
                }
            )

        proof_number = attrs.get("proof_number")

        if not proof_number:
            raise serializers.ValidationError(
                {
                    "proof_number": "Proof number is required."
                }
            )

        if verification_type in [
            User.Role.POLICE_OFFICER,
            User.Role.INVESTIGATOR,
            User.Role.LEGAL_OFFICER,
        ]:
            if not attrs.get("department"):
                raise serializers.ValidationError(
                    {
                        "department": "Department is required."
                    }
                )

            if not attrs.get("designation"):
                raise serializers.ValidationError(
                    {
                        "designation": "Designation is required."
                    }
                )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        return UserVerification.objects.create(
            user=user,
            **validated_data,
        )


class AdminUserSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()
    verification_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "department",
            "role",
            "is_active",
            "verification_status",
            "verification_id",
            "date_joined",
            "created_at",
            "updated_at",
            "last_login",
        ]

        read_only_fields = fields

    def get_verification_status(self, obj):
        verification = getattr(
            obj,
            "verification",
            None,
        )

        if verification is None:
            return "NOT_SUBMITTED"

        return verification.status

    def get_verification_id(self, obj):
        verification = getattr(
            obj,
            "verification",
            None,
        )

        if verification is None:
            return None

        return verification.id


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "department",
        ]

    def validate_email(self, value):
        value = value.strip()

        queryset = User.objects.filter(
            email__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if value and queryset.exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value


class AdminVerificationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    user_id = serializers.IntegerField(
        source="user.id",
        read_only=True,
    )

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    user_role = serializers.CharField(
        source="user.role",
        read_only=True,
    )

    verified_by_username = serializers.SerializerMethodField()

    class Meta:
        model = UserVerification
        fields = [
            "id",
            "user_id",
            "username",
            "user_email",
            "user_role",
            "verification_type",
            "proof_number",
            "proof_document",
            "photo",
            "department",
            "designation",
            "status",
            "verified_by",
            "verified_by_username",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_verified_by_username(self, obj):
        if obj.verified_by is None:
            return None

        return obj.verified_by.username

from django.contrib import admin

from .models import User, UserVerification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_active",
        "date_joined",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "date_joined",
        "last_login",
    )

    ordering = (
        "-created_at",
    )


@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "verification_type",
        "status",
        "department",
        "designation",
        "verified_by",
        "verified_at",
        "created_at",
    )

    list_filter = (
        "verification_type",
        "status",
        "department",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "proof_number",
        "department",
        "designation",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "verified_at",
    )

    ordering = (
        "-created_at",
    )

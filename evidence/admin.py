from django.contrib import admin

from .models import (
    Evidence,
    EvidenceActivity,
    EvidenceCustodyTransfer,
)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):

    list_display = (
        "evidence_number",
        "title",
        "case",
        "evidence_type",
        "collected_by",
        "current_custodian",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "evidence_type",
        "is_archived",
        "created_at",
    )

    search_fields = (
        "evidence_number",
        "title",
        "description",
        "original_filename",
        "sha256_hash",
    )

    readonly_fields = (
        "evidence_number",
        "original_filename",
        "file_size",
        "mime_type",
        "sha256_hash",
        "collected_by",
        "current_custodian",
        "created_at",
        "updated_at",
    )


@admin.register(EvidenceCustodyTransfer)
class EvidenceCustodyTransferAdmin(
    admin.ModelAdmin
):

    list_display = (
        "evidence",
        "from_user",
        "to_user",
        "transferred_by",
        "transfer_type",
        "location",
        "transferred_at",
    )

    list_filter = (
        "transfer_type",
        "transferred_at",
    )

    search_fields = (
        "evidence__evidence_number",
        "evidence__title",
        "from_user__username",
        "to_user__username",
        "transferred_by__username",
        "reason",
        "location",
        "sha256_hash",
    )

    readonly_fields = (
        "evidence",
        "from_user",
        "to_user",
        "transferred_by",
        "transfer_type",
        "reason",
        "location",
        "sha256_hash",
        "transferred_at",
        "created_at",
    )


@admin.register(EvidenceActivity)
class EvidenceActivityAdmin(
    admin.ModelAdmin
):

    list_display = (
        "evidence",
        "actor",
        "action",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "evidence__evidence_number",
        "evidence__title",
        "actor__username",
        "description",
    )

    readonly_fields = (
        "evidence",
        "actor",
        "action",
        "description",
        "metadata",
        "created_at",
    )

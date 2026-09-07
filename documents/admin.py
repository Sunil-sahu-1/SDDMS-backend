from django.contrib import admin

from .models import (
    Document,
    DocumentShare,
    DocumentVersion,
    DocumentSignature,
)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "case",
        "document_type",
        "version",
        "uploaded_by",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "document_type",
        "is_archived",
        "created_at",
    )

    search_fields = (
        "title",
        "original_filename",
        "sha256_hash",
    )

    readonly_fields = (
        "original_filename",
        "file_size",
        "mime_type",
        "sha256_hash",
        "version",
        "uploaded_by",
        "is_archived",
        "created_at",
        "updated_at",
    )


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "version_number",
        "uploaded_by",
        "sha256_hash",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "document__title",
        "original_filename",
        "sha256_hash",
    )

    readonly_fields = (
        "document",
        "version_number",
        "file",
        "original_filename",
        "file_size",
        "mime_type",
        "sha256_hash",
        "uploaded_by",
        "change_note",
        "created_at",
    )


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "shared_with",
        "permission",
        "shared_by",
        "expires_at",
        "is_active",
        "created_at",
    )

    list_filter = (
        "permission",
        "is_active",
        "created_at",
    )

    search_fields = (
        "document__title",
        "shared_with__username",
        "shared_by__username",
    )

    readonly_fields = (
        "document",
        "shared_with",
        "shared_by",
        "created_at",
    )


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "signed_by",
        "version",
        "algorithm",
        "signed_at",
    )

    list_filter = (
        "algorithm",
        "signed_at",
    )

    search_fields = (
        "document__title",
        "signed_by__username",
        "document_hash",
    )

    readonly_fields = (
        "document",
        "signed_by",
        "version",
        "document_hash",
        "signature",
        "algorithm",
        "signed_at",
    )

    list_select_related = (
        "document",
        "signed_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

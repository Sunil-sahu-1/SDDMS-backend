from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "action",
        "case",
        "document",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "case__case_number",
        "document__title",
        "description",
        "ip_address",
        "record_hash",
        "previous_hash",
    )

    readonly_fields = (
        "user",
        "action",
        "case",
        "document",
        "description",
        "ip_address",
        "user_agent",
        "metadata",
        "previous_hash",
        "record_hash",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "user",
        "case",
        "document",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

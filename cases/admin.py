from django.contrib import admin

from .models import Case, CaseHistory


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_number",
        "fir_number",
        "title",
        "status",
        "complainant",
        "assigned_officer",
        "assigned_investigator",
        "created_by",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "case_number",
        "fir_number",
        "title",
        "description",
        "complainant__username",
        "assigned_officer__username",
        "assigned_investigator__username",
        "created_by__username",
    )

    list_select_related = (
        "complainant",
        "assigned_officer",
        "assigned_investigator",
        "created_by",
    )

    readonly_fields = (
        "case_number",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(CaseHistory)
class CaseHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "case",
        "changed_by",
        "old_status",
        "new_status",
        "comment",
        "created_at",
    )

    list_filter = (
        "old_status",
        "new_status",
        "created_at",
    )

    search_fields = (
        "case__case_number",
        "changed_by__username",
        "comment",
    )

    list_select_related = (
        "case",
        "changed_by",
    )

    readonly_fields = (
        "case",
        "changed_by",
        "old_status",
        "new_status",
        "comment",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

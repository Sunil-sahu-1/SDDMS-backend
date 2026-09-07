from django.contrib import admin

from .models import Investigation, WitnessStatement


@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = (
        "investigation_number",
        "case",
        "title",
        "lead_investigator",
        "status",
        "priority",
        "started_at",
        "completed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "started_at",
        "completed_at",
        "created_at",
    )

    search_fields = (
        "investigation_number",
        "title",
        "description",
        "case__case_number",
        "lead_investigator__username",
        "assigned_officers__username",
    )

    filter_horizontal = (
        "assigned_officers",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(WitnessStatement)
class WitnessStatementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "witness_name",
        "recorded_by",
        "statement_date",
        "status",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "status",
        "is_archived",
        "statement_date",
        "created_at",
    )

    search_fields = (
        "witness_name",
        "witness_contact",
        "statement",
        "case__case_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

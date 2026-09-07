from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):

    list_display = (
        "complaint_number",
        "subject",
        "complainant",
        "status",
        "case",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "complaint_number",
        "subject",
        "description",
        "complainant__username",
        "complainant__email",
        "case__case_number",
    )

    list_select_related = (
        "complainant",
        "case",
    )

    readonly_fields = (
        "complaint_number",
        "complainant",
        "status",
        "case",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

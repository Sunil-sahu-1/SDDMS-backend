from django.conf import settings
from django.db import models


class Case(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        UNDER_INVESTIGATION = (
            "UNDER_INVESTIGATION",
            "Under Investigation",
        )
        CHARGESHEET_FILED = (
            "CHARGESHEET_FILED",
            "Chargesheet Filed",
        )
        COURT = "COURT", "Court"
        CLOSED = "CLOSED", "Closed"

    case_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    fir_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaints_cases",
        null=True,
        blank=True,
    )

    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="police_cases",
        null=True,
        blank=True,
    )

    assigned_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="investigation_cases",
        null=True,
        blank=True,
    )

    assigned_legal_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="legal_cases",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cases",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_number} - {self.title}"


class CaseHistory(models.Model):

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="history",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    old_status = models.CharField(
        max_length=30,
        blank=True,
    )

    new_status = models.CharField(
        max_length=30,
    )

    comment = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.case.case_number}: "
            f"{self.old_status} -> {self.new_status}"
        )
from django.conf import settings
from django.db import models

from cases.models import Case


class Investigation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On Hold"
        COMPLETED = "COMPLETED", "Completed"
        CLOSED = "CLOSED", "Closed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    investigation_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.PROTECT,
        related_name="investigations",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lead_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_investigations",
        null=True,
        blank=True,
    )
    assigned_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_investigations",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_investigations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="inv_status_created_idx",
            ),
            models.Index(
                fields=["case", "-created_at"],
                name="inv_case_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.investigation_number} - {self.title}"


class InvestigationHistory(models.Model):
    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name="timeline",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investigation_history_changes",
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["investigation", "-created_at"],
                name="inv_history_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.investigation.investigation_number}: "
            f"{self.old_status} -> {self.new_status}"
        )


class WitnessStatement(models.Model):
    class StatementStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        VERIFIED = "VERIFIED", "Verified"
        FINAL = "FINAL", "Final"
        ARCHIVED = "ARCHIVED", "Archived"

    class Classification(models.TextChoices):
        CONFIDENTIAL = "CONFIDENTIAL", "Confidential"
        HIGHLY_CONFIDENTIAL = "HIGHLY_CONFIDENTIAL", "Highly Confidential"
        RESTRICTED = "RESTRICTED", "Restricted"

    case = models.ForeignKey(
        Case,
        on_delete=models.PROTECT,
        related_name="witness_statements",
    )
    statement_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    witness_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )
    witness_name = models.CharField(max_length=255)
    witness_contact = models.CharField(max_length=100, blank=True)
    statement = models.TextField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_witness_statements",
    )
    statement_date = models.DateTimeField()
    classification = models.CharField(
        max_length=30,
        choices=Classification.choices,
        default=Classification.CONFIDENTIAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=StatementStatus.choices,
        default=StatementStatus.DRAFT,
        db_index=True,
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-statement_date"]
        indexes = [
            models.Index(
                fields=["case", "-statement_date"],
                name="ws_case_date_idx",
            ),
            models.Index(
                fields=["status", "-statement_date"],
                name="ws_status_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.statement_number or self.witness_name} - {self.case}"


class WitnessStatementMedia(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        VIDEO = "VIDEO", "Video"

    statement = models.ForeignKey(
        WitnessStatement,
        on_delete=models.CASCADE,
        related_name="media",
    )
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        db_index=True,
    )
    file = models.FileField(
        upload_to="witness_statements/%Y/%m/%d/",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_witness_statement_media",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["statement", "-created_at"],
                name="wsm_statement_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.statement_id} - {self.media_type}"
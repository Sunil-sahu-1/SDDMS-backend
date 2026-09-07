from django.conf import settings
from django.db import models


class Evidence(models.Model):

    class EvidenceType(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document"
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        AUDIO = "AUDIO", "Audio"
        PHYSICAL = "PHYSICAL", "Physical"
        OTHER = "OTHER", "Other"

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="evidence_records"
    )

    evidence_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    title = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True
    )

    evidence_type = models.CharField(
        max_length=20,
        choices=EvidenceType.choices
    )

    file = models.FileField(
        upload_to="evidence/%Y/%m/"
    )

    original_filename = models.CharField(
        max_length=255
    )

    file_size = models.PositiveBigIntegerField(
        default=0
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True
    )

    sha256_hash = models.CharField(
        max_length=64,
        db_index=True
    )

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collected_evidence"
    )

    # Current person who has physical/logical custody
    current_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="custody_evidence",
        null=True,
        blank=True,
    )

    is_archived = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.evidence_number} - "
            f"{self.title}"
        )


class EvidenceCustodyTransfer(models.Model):

    class TransferType(models.TextChoices):
        INITIAL = "INITIAL", "Initial Custody"
        TRANSFER = "TRANSFER", "Transfer"
        RETURN = "RETURN", "Return"

    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="custody_transfers"
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_custody_from",
        null=True,
        blank=True,
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_custody_to",
    )

    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_evidence_transfers",
    )

    transfer_type = models.CharField(
        max_length=20,
        choices=TransferType.choices,
        default=TransferType.TRANSFER,
    )

    reason = models.TextField(
        blank=True
    )

    location = models.CharField(
        max_length=255,
        blank=True
    )

    sha256_hash = models.CharField(
        max_length=64
    )

    transferred_at = models.DateTimeField(
        auto_now_add=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-transferred_at"]
        indexes = [
            models.Index(
                fields=[
                    "evidence",
                    "-transferred_at"
                ],
                name="custody_evidence_date_idx"
            ),
            models.Index(
                fields=[
                    "to_user",
                    "-transferred_at"
                ],
                name="custody_to_user_date_idx"
            ),
        ]

    def __str__(self):
        return (
            f"{self.evidence.evidence_number} - "
            f"{self.from_user} -> {self.to_user}"
        )


class EvidenceActivity(models.Model):

    class Action(models.TextChoices):
        UPLOAD = "UPLOAD", "Upload"
        TRANSFER = "TRANSFER", "Transfer"
        DOWNLOAD = "DOWNLOAD", "Download"
        VERIFY = "VERIFY", "Integrity Verification"
        UPDATE = "UPDATE", "Update"
        ARCHIVE = "ARCHIVE", "Archive"

    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_activities"
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices
    )

    description = models.TextField(
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=[
                    "evidence",
                    "-created_at"
                ],
                name="activity_evidence_date_idx"
            ),
        ]

    def __str__(self):
        return (
            f"{self.evidence.evidence_number} - "
            f"{self.action}"
        )

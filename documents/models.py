import hashlib

from django.db import models

from accounts.models import User
from cases.models import Case


class Document(models.Model):
    class DocumentType(models.TextChoices):
        FIR = "FIR", "FIR"
        POLICE_REPORT = "POLICE_REPORT", "Police Report"
        INVESTIGATION_REPORT = "INVESTIGATION_REPORT", "Investigation Report"
        LEGAL_DOCUMENT = "LEGAL_DOCUMENT", "Legal Document"
        COURT_DOCUMENT = "COURT_DOCUMENT", "Court Document"
        EVIDENCE = "EVIDENCE", "Evidence"
        COMPLAINT_DOCUMENT = "COMPLAINT_DOCUMENT", "Complaint Document"
        GENERAL = "GENERAL", "General"
        OTHER = "OTHER", "Other"

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(max_length=255)

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )

    file = models.FileField(upload_to="documents/")

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    file_size = models.BigIntegerField(default=0)

    mime_type = models.CharField(
        max_length=255,
        blank=True,
    )

    sha256_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    version = models.PositiveIntegerField(default=1)

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )

    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def calculate_sha256(self):
        if not self.file:
            return ""

        self.file.seek(0)

        sha256 = hashlib.sha256()

        for chunk in self.file.chunks():
            sha256.update(chunk)

        self.file.seek(0)

        return sha256.hexdigest()

    def save(self, *args, **kwargs):
        if self.file:
            self.sha256_hash = self.calculate_sha256()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    file = models.FileField(
        upload_to="documents/versions/",
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    file_size = models.BigIntegerField(default=0)

    mime_type = models.CharField(
        max_length=255,
        blank=True,
    )

    sha256_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="document_versions",
    )

    change_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "document",
                    "version_number",
                ],
                name="unique_document_version",
            )
        ]

    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"


class DocumentShare(models.Model):
    class Permission(models.TextChoices):
        VIEW = "VIEW", "View"
        DOWNLOAD = "DOWNLOAD", "Download"
        EDIT = "EDIT", "Edit"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="shares",
    )

    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_document_shares",
    )

    shared_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_document_shares",
    )

    permission = models.CharField(
        max_length=20,
        choices=Permission.choices,
        default=Permission.VIEW,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "document",
                    "shared_with",
                ],
                name="unique_document_share",
            )
        ]

    def __str__(self):
        return f"{self.document.title} - {self.shared_with.username}"


class DocumentSignature(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="signatures",
    )

    signed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="document_signatures",
    )

    version = models.PositiveIntegerField()

    document_hash = models.CharField(max_length=64)

    signature = models.TextField()

    algorithm = models.CharField(
        max_length=100,
        default="RSA-SHA256",
    )

    signed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.title} - Signature {self.id}"
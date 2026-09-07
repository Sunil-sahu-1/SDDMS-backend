from django.conf import settings
from django.db import models
from django.utils import timezone

from cases.models import Case
from documents.models import Document


class AuditLog(models.Model):

    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        VIEW = "VIEW", "View"
        DOWNLOAD = "DOWNLOAD", "Download"
        UPLOAD = "UPLOAD", "Upload"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        ARCHIVE = "ARCHIVE", "Archive"
        SHARE = "SHARE", "Share"
        VERIFY = "VERIFY", "Verify"
        ACCESS_DENIED = "ACCESS_DENIED", "Access Denied"
        USER_UPDATED = "USER_UPDATED", "User Updated"
        USER_DELETED = "USER_DELETED", "User Deleted"
        USER_ROLE_CHANGED = "USER_ROLE_CHANGED", "User Role Changed"
        USER_STATUS_CHANGED = "USER_STATUS_CHANGED", "User Status Changed"
        VERIFICATION_APPROVED = "VERIFICATION_APPROVED", "Verification Approved"
        VERIFICATION_REJECTED = "VERIFICATION_REJECTED", "Verification Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    description = models.TextField(
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    previous_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        editable=False,
    )

    record_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="audit_user_created_idx",
            ),
            models.Index(
                fields=["action", "-created_at"],
                name="audit_action_created_idx",
            ),
            models.Index(
                fields=["case", "-created_at"],
                name="audit_case_created_idx",
            ),
            models.Index(
                fields=["document", "-created_at"],
                name="audit_doc_created_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "Audit logs are immutable and cannot be updated."
            )

        if not self.created_at:
            self.created_at = timezone.now()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "Audit logs are immutable and cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.action} - "
            f"{self.created_at}"
        )

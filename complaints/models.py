from django.conf import settings
from django.db import models


class Complaint(models.Model):

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        CONVERTED_TO_CASE = (
            "CONVERTED_TO_CASE",
            "Converted to Case",
        )
        CLOSED = "CLOSED", "Closed"

    complaint_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaints",
    )

    subject = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )

    case = models.OneToOneField(
        "cases.Case",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint",
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
        return (
            f"{self.complaint_number} - "
            f"{self.subject}"
        )

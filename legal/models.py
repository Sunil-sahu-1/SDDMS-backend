from django.conf import settings
from django.db import models

from cases.models import Case


class LegalReview(models.Model):

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CLOSED = "CLOSED", "Closed"

    case = models.ForeignKey(
        Case,
        on_delete=models.PROTECT,
        related_name="legal_reviews",
    )

    legal_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legal_reviews",
    )

    title = models.CharField(
        max_length=255
    )

    legal_opinion = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )

    remarks = models.TextField(
        blank=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
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
        return f"{self.title} - {self.case}"


class CourtHearing(models.Model):

    class HearingStatus(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        ADJOURNED = "ADJOURNED", "Adjourned"
        CANCELLED = "CANCELLED", "Cancelled"

    case = models.ForeignKey(
        Case,
        on_delete=models.PROTECT,
        related_name="court_hearings",
    )

    legal_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="court_hearings",
    )

    court_name = models.CharField(
        max_length=255
    )

    hearing_date = models.DateTimeField()

    hearing_purpose = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=HearingStatus.choices,
        default=HearingStatus.SCHEDULED,
    )

    outcome = models.TextField(
        blank=True
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
        ordering = ["hearing_date"]

    def __str__(self):
        return f"{self.court_name} - {self.case}"

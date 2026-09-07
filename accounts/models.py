from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):

    class Role(models.TextChoices):
        NORMAL_USER = "NORMAL_USER", "Normal User"
        POLICE_OFFICER = "POLICE_OFFICER", "Police Officer"
        INVESTIGATOR = "INVESTIGATOR", "Investigator"
        LEGAL_OFFICER = "LEGAL_OFFICER", "Legal Officer"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.NORMAL_USER,
        db_index=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    department = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    # Used by Admin to activate/deactivate an account.
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.username} - {self.role}"


class UserVerification(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    class VerificationType(models.TextChoices):
        NORMAL_USER = "NORMAL_USER", "Normal User"
        POLICE_OFFICER = "POLICE_OFFICER", "Police Officer"
        INVESTIGATOR = "INVESTIGATOR", "Investigator"
        LEGAL_OFFICER = "LEGAL_OFFICER", "Legal Officer"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="verification",
    )

    verification_type = models.CharField(
        max_length=30,
        choices=VerificationType.choices,
        db_index=True,
    )

    proof_number = models.CharField(
        max_length=100,
    )

    proof_document = models.FileField(
        upload_to="verification/proofs/",
    )

    photo = models.ImageField(
        upload_to="verification/photos/",
    )

    department = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    designation = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Admin/staff member who approved or rejected the verification.
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_users",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Useful when an Admin rejects a verification.
    rejection_reason = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [ models.Index( fields=["status", "-created_at"],name="ver_status_created_idx",),
    models.Index( fields=["verification_type", "status"], name="ver_type_status_idx",),
]


    def clean(self):
        """
        Keep the verification type consistent with the user's role.

        ADMIN accounts do not go through this verification workflow.
        """

        if not self.user_id:
            return

        if self.user.role == User.Role.ADMIN:
            raise ValidationError(
                {
                    "verification_type": (
                        "Admin accounts cannot use the normal user "
                        "verification workflow."
                    )
                }
            )

        if self.verification_type != self.user.role:
            raise ValidationError(
                {
                    "verification_type": (
                        "Verification type must match the user's role."
                    )
                }
            )

    def save(self, *args, **kwargs):
        """
        Automatically maintain verification review metadata.
        """

        if self.status == self.Status.VERIFIED:
            if self.verified_at is None:
                self.verified_at = timezone.now()

            # A verified record should not retain an old rejection reason.
            self.rejection_reason = None

        elif self.status == self.Status.REJECTED:
            if self.verified_at is None:
                self.verified_at = timezone.now()

        elif self.status == self.Status.PENDING:
            self.verified_by = None
            self.verified_at = None
            self.rejection_reason = None

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

"""Domain models for the tenant-scoped landlord portal."""

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from portal.constants import (
    DocumentType,
    InterventionType,
    OperationStatus,
    ProcessRole,
    ProcessStatus,
)


class Process(models.Model):
    """A forestry management process tied to one or more senhorios."""

    name = models.CharField(max_length=255)
    reference_code = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=ProcessStatus.choices,
        default=ProcessStatus.ACTIVE,
    )
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_processes",
        help_text="Internal process manager.",
    )
    workos_organization_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional WorkOS organization id used for external RBAC scoping.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "processes"

    def __str__(self) -> str:
        return f"{self.reference_code} — {self.name}"


class ProcessMembership(models.Model):
    """
    Multiple users per process (co-owners, heirs, accountant).

    Links the locally synchronized AuthKit user to a process and a business role.
    """

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="process_memberships",
    )
    role = models.CharField(max_length=32, choices=ProcessRole.choices)
    workos_user_id = models.CharField(max_length=255, blank=True)
    notify_by_email = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("process", "user")]

    def __str__(self) -> str:
        return f"{self.user} → {self.process} ({self.role})"


class ProcessDocument(models.Model):
    """
    Process documentation: contracts, forest plan, annual reports, invoices.

    Files live in private object storage; only storage_key is persisted here.
    """

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    storage_key = models.CharField(
        max_length=512,
        help_text="Private object storage key (S3/R2/MinIO).",
    )
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title


class ParcelPhoto(models.Model):
    """Parcel photo gallery entry for timelapse / chronological views."""

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    parcel_label = models.CharField(max_length=128, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    storage_key = models.CharField(max_length=512)
    captured_at = models.DateTimeField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["captured_at"]

    def __str__(self) -> str:
        return f"{self.parcel_label or 'Parcel'} @ {self.captured_at:%Y-%m-%d}"


class Intervention(models.Model):
    """Historical record of on-the-ground interventions."""

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="interventions",
    )
    intervention_type = models.CharField(
        max_length=32,
        choices=InterventionType.choices,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    performed_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return self.title


class ScheduledOperation(models.Model):
    """Calendar of planned forestry operations."""

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="scheduled_operations",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_start = models.DateField()
    scheduled_end = models.DateField(null=True, blank=True)
    location_notes = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32,
        choices=OperationStatus.choices,
        default=OperationStatus.PLANNED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_start"]

    def __str__(self) -> str:
        return f"{self.title} ({self.scheduled_start})"


class MessageThread(models.Model):
    """Communication channel between senhorio and process manager."""

    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="message_threads",
    )
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.subject


class Message(models.Model):
    thread = models.ForeignKey(
        MessageThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class NotificationPreference(models.Model):
    """
    Email notifications for new documents or calendar events.

    Placeholder: per-user preferences per process.
    """

    membership = models.OneToOneField(
        ProcessMembership,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    notify_new_documents = models.BooleanField(default=True)
    notify_new_messages = models.BooleanField(default=True)
    notify_upcoming_operations = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Notifications for {self.membership}"


class AccessLog(models.Model):
    """GDPR audit trail of access to sensitive resources."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    workos_user_id = models.CharField(max_length=255, blank=True)
    process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    resource_type = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=32)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accessed_at"]

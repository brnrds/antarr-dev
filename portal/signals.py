"""Portal domain events that schedule user notifications after commit."""

from collections.abc import Callable

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from portal.models import (
    Message,
    NotificationPreference,
    ProcessDocument,
    ScheduledOperation,
)
from portal.services.notifications import (
    notify_new_document,
    notify_new_message,
    notify_upcoming_operation,
)


def _recipients(process, preference_field: str, *, exclude_user_id=None):
    memberships = process.memberships.select_related("user").filter(
        notify_by_email=True,
        user__email__gt="",
    )
    if exclude_user_id:
        memberships = memberships.exclude(user_id=exclude_user_id)
    for membership in memberships:
        preference = NotificationPreference.objects.filter(
            membership=membership
        ).first()
        if preference is None or getattr(preference, preference_field):
            yield membership.user.email


def _after_commit(callback: Callable[[], None]) -> None:
    transaction.on_commit(callback)


@receiver(post_save, sender=ProcessDocument)
def document_created(sender, instance, created, **kwargs):
    if not created:
        return
    for email in _recipients(instance.process, "notify_new_documents"):
        _after_commit(
            lambda email=email: notify_new_document(
                recipient_email=email,
                process_name=instance.process.name,
                document_title=instance.title,
            )
        )


@receiver(post_save, sender=ScheduledOperation)
def operation_created(sender, instance, created, **kwargs):
    if not created:
        return
    for email in _recipients(instance.process, "notify_upcoming_operations"):
        _after_commit(
            lambda email=email: notify_upcoming_operation(
                recipient_email=email,
                process_name=instance.process.name,
                operation_title=instance.title,
            )
        )


@receiver(post_save, sender=Message)
def message_created(sender, instance, created, **kwargs):
    if not created:
        return
    process = instance.thread.process
    for email in _recipients(
        process,
        "notify_new_messages",
        exclude_user_id=instance.author_id,
    ):
        _after_commit(
            lambda email=email: notify_new_message(
                recipient_email=email,
                process_name=process.name,
                subject=instance.thread.subject,
            )
        )

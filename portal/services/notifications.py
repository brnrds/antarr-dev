"""Transactional email notifications for portal activity."""

from __future__ import annotations

from django.core.mail import send_mail


def notify_new_document(
    *,
    recipient_email: str,
    process_name: str,
    document_title: str,
) -> None:
    send_mail(
        subject=f"[Antarr] Novo documento: {document_title}",
        message=(
            f"Foi publicado um novo documento no processo “{process_name}”: "
            f"{document_title}.\n\nConsulte-o na sua área reservada."
        ),
        from_email=None,
        recipient_list=[recipient_email],
        fail_silently=True,
    )


def notify_upcoming_operation(
    *,
    recipient_email: str,
    process_name: str,
    operation_title: str,
) -> None:
    send_mail(
        subject=f"[Antarr] Nova operação prevista: {operation_title}",
        message=(
            f"A operação “{operation_title}” foi adicionada ao calendário do "
            f"processo “{process_name}”.\n\nConsulte os detalhes na sua área reservada."
        ),
        from_email=None,
        recipient_list=[recipient_email],
        fail_silently=True,
    )


def notify_new_message(
    *,
    recipient_email: str,
    process_name: str,
    subject: str,
) -> None:
    send_mail(
        subject=f"[Antarr] Nova mensagem: {subject}",
        message=(
            f"Recebeu uma nova mensagem no processo “{process_name}”.\n\n"
            "Consulte-a e responda através da sua área reservada."
        ),
        from_email=None,
        recipient_list=[recipient_email],
        fail_silently=True,
    )

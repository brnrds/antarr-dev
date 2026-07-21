"""Tenant-scoped views for the landlord portal."""

from __future__ import annotations

from django.contrib import messages as django_messages
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from portal.constants import DocumentType
from portal.decorators import require_portal_login
from portal.models import (
    AccessLog,
    Intervention,
    Message,
    MessageThread,
    NotificationPreference,
    ParcelPhoto,
    Process,
    ProcessDocument,
    ProcessMembership,
    ScheduledOperation,
)
from portal.services.storage import (
    InvalidDownloadToken,
    PrivateObjectStorage,
    StoredObjectNotFound,
)


def _client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else None) or request.META.get(
        "REMOTE_ADDR"
    )


def _accessible_processes(request: HttpRequest):
    """Return only processes the current identity is allowed to access."""
    user = request.portal_user
    queryset = Process.objects.filter(is_active=True).select_related("manager")
    if not (user.is_staff or user.is_superuser):
        queryset = queryset.filter(memberships__user=user)
    return queryset.distinct().order_by("reference_code")


def _portal_context(request: HttpRequest) -> dict:
    processes = list(_accessible_processes(request))
    requested_id = request.GET.get("process") or request.POST.get("process")
    current_process = next(
        (process for process in processes if str(process.pk) == str(requested_id)),
        processes[0] if processes else None,
    )
    workos_user = request.session.get("workos_user", {})
    display_name = (
        workos_user.get("first_name")
        or request.portal_user.first_name
        or request.portal_user.email
        or request.portal_user.username
    )
    return {
        "portal_processes": processes,
        "current_process": current_process,
        "workos_user": workos_user,
        "portal_user": request.portal_user,
        "display_name": display_name,
    }


def _process_filter(context: dict) -> Q:
    process = context["current_process"]
    if process is None:
        return Q(pk__in=[])
    return Q(process=process)


@require_portal_login
def dashboard(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    process = context["current_process"]
    today = timezone.localdate()

    if process:
        upcoming = process.scheduled_operations.filter(
            scheduled_start__gte=today
        ).first()
        recent_documents = list(process.documents.all()[:3])
        recent_interventions = list(process.interventions.all()[:3])
        activity = sorted(
            [
                *[(doc.published_at, "document", doc) for doc in recent_documents],
                *[
                    (
                        timezone.make_aware(
                            timezone.datetime.combine(
                                item.performed_at, timezone.datetime.min.time()
                            )
                        ),
                        "intervention",
                        item,
                    )
                    for item in recent_interventions
                ],
            ],
            key=lambda entry: entry[0],
            reverse=True,
        )[:4]
        context.update(
            {
                "upcoming_operation": upcoming,
                "recent_activity": activity,
                "stats": {
                    "documents": process.documents.count(),
                    "photos": process.photos.count(),
                    "interventions": process.interventions.count(),
                    "upcoming": process.scheduled_operations.filter(
                        scheduled_start__gte=today
                    ).count(),
                },
                "members": process.memberships.select_related("user").all()[:4],
            }
        )

    return render(request, "portal/dashboard.html", context)


@require_portal_login
def documents(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    queryset = ProcessDocument.objects.select_related("process").filter(
        _process_filter(context)
    )
    selected_type = request.GET.get("type", "")
    if selected_type in DocumentType.values:
        queryset = queryset.filter(document_type=selected_type)
    context.update(
        {
            "documents": queryset,
            "document_types": DocumentType.choices,
            "selected_type": selected_type,
        }
    )
    return render(request, "portal/documents.html", context)


@require_portal_login
def document_download(request: HttpRequest, document_id: int) -> HttpResponse:
    allowed_processes = _accessible_processes(request)
    document = get_object_or_404(
        ProcessDocument.objects.select_related("process"),
        pk=document_id,
        process__in=allowed_processes,
    )
    AccessLog.objects.create(
        user=request.portal_user,
        workos_user_id=request.session.get("workos_user", {}).get("id", ""),
        process=document.process,
        resource_type="document",
        resource_id=str(document.pk),
        action="download_requested",
        ip_address=_client_ip(request),
    )
    signed = PrivateObjectStorage().get_download_url(document.storage_key)
    return redirect(signed.url)


@require_portal_login
def photo_image(request: HttpRequest, photo_id: int) -> HttpResponse:
    photo = get_object_or_404(
        ParcelPhoto,
        pk=photo_id,
        process__in=_accessible_processes(request),
    )
    signed = PrivateObjectStorage().get_download_url(photo.storage_key)
    return redirect(signed.url)


@require_portal_login
def signed_file(request: HttpRequest) -> HttpResponse:
    token = request.GET.get("token", "")
    try:
        stored_object = PrivateObjectStorage().open_signed_download(token)
    except InvalidDownloadToken as exc:
        raise Http404("This download link is invalid or has expired.") from exc
    except StoredObjectNotFound as exc:
        raise Http404("The requested file is not available in local storage.") from exc

    allowed_processes = _accessible_processes(request)
    document = ProcessDocument.objects.filter(
        storage_key=stored_object.storage_key, process__in=allowed_processes
    ).first()
    photo = ParcelPhoto.objects.filter(
        storage_key=stored_object.storage_key, process__in=allowed_processes
    ).first()
    resource = document or photo
    if resource is None:
        stored_object.stream.close()
        raise Http404("The requested resource is not available.")

    AccessLog.objects.create(
        user=request.portal_user,
        process=resource.process,
        resource_type="document" if document else "photo",
        resource_id=str(resource.pk),
        action="downloaded" if document else "viewed",
        ip_address=_client_ip(request),
    )
    return FileResponse(
        stored_object.stream,
        as_attachment=document is not None,
        filename=stored_object.filename,
    )


@require_portal_login
def photos(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    queryset = ParcelPhoto.objects.select_related("process").filter(
        _process_filter(context)
    )
    parcel = request.GET.get("parcel", "")
    if parcel:
        queryset = queryset.filter(parcel_label=parcel)
    context.update(
        {
            "photos": queryset.order_by("-captured_at"),
            "parcel_labels": queryset.order_by()
            .exclude(parcel_label="")
            .values_list("parcel_label", flat=True)
            .distinct(),
            "selected_parcel": parcel,
        }
    )
    return render(request, "portal/photos.html", context)


@require_portal_login
def interventions(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    context["interventions"] = Intervention.objects.select_related("process").filter(
        _process_filter(context)
    )
    return render(request, "portal/interventions.html", context)


@require_portal_login
def calendar_view(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    operations = ScheduledOperation.objects.select_related("process").filter(
        _process_filter(context)
    )
    today = timezone.localdate()
    context.update(
        {
            "upcoming_operations": operations.filter(scheduled_start__gte=today),
            "past_operations": operations.filter(scheduled_start__lt=today).order_by(
                "-scheduled_start"
            )[:10],
            "today": today,
        }
    )
    return render(request, "portal/calendar.html", context)


@require_portal_login
def messages(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    threads = (
        MessageThread.objects.select_related("process")
        .filter(_process_filter(context))
        .annotate(message_count=Count("messages"))
    )
    active_thread = None
    requested_thread = request.GET.get("thread")
    if requested_thread:
        active_thread = threads.filter(pk=requested_thread).first()
    if active_thread is None:
        active_thread = threads.first()
    context.update({"threads": threads, "active_thread": active_thread})
    return render(request, "portal/messages.html", context)


@require_POST
@require_portal_login
def send_message(request: HttpRequest) -> HttpResponse:
    body = request.POST.get("body", "").strip()
    process = get_object_or_404(
        _accessible_processes(request), pk=request.POST.get("process")
    )
    thread_id = request.POST.get("thread")
    thread = None
    if thread_id:
        thread = get_object_or_404(MessageThread, pk=thread_id, process=process)
    if thread is None and body:
        subject = request.POST.get("subject", "").strip()[:255] or "Nova mensagem"
        thread = MessageThread.objects.create(process=process, subject=subject)
    if body and thread:
        Message.objects.create(thread=thread, author=request.portal_user, body=body)
        thread.save(update_fields=["updated_at"])
        django_messages.success(request, "A sua mensagem foi enviada.")
    else:
        django_messages.error(request, "Escreva uma mensagem antes de enviar.")
    thread_pk = thread.pk if thread else ""
    base_path = request.path.rsplit("send/", 1)[0]
    return redirect(f"{base_path}?process={process.pk}&thread={thread_pk}")


@require_portal_login
def security_settings(request: HttpRequest) -> HttpResponse:
    context = _portal_context(request)
    membership = None
    process = context["current_process"]
    if process:
        membership = ProcessMembership.objects.filter(
            process=process, user=request.portal_user
        ).first()
    preference = None
    if membership:
        preference, _ = NotificationPreference.objects.get_or_create(
            membership=membership
        )
    context.update(
        {
            "membership": membership,
            "preference": preference,
            "recent_accesses": AccessLog.objects.filter(user=request.portal_user)[:8],
        }
    )
    return render(request, "portal/security.html", context)


@require_POST
@require_portal_login
def update_notifications(request: HttpRequest) -> HttpResponse:
    process = get_object_or_404(
        _accessible_processes(request), pk=request.POST.get("process")
    )
    membership = get_object_or_404(
        ProcessMembership, process=process, user=request.portal_user
    )
    preference, _ = NotificationPreference.objects.get_or_create(membership=membership)
    for field in (
        "notify_new_documents",
        "notify_new_messages",
        "notify_upcoming_operations",
    ):
        setattr(preference, field, field in request.POST)
    preference.save()
    django_messages.success(request, "Preferências de notificação atualizadas.")
    base_path = request.path.rsplit("notifications/", 1)[0]
    return redirect(f"{base_path}?process={process.pk}")

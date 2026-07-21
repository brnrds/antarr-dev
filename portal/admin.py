from django.contrib import admin

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


class ProcessMembershipInline(admin.TabularInline):
    model = ProcessMembership
    extra = 0


class ProcessDocumentInline(admin.TabularInline):
    model = ProcessDocument
    extra = 0


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "name",
        "location",
        "status",
        "progress_percent",
        "manager",
        "is_active",
    )
    list_filter = ("status", "is_active")
    search_fields = ("reference_code", "name", "location")
    inlines = [ProcessMembershipInline, ProcessDocumentInline]


@admin.register(ProcessMembership)
class ProcessMembershipAdmin(admin.ModelAdmin):
    list_display = ("process", "user", "role", "notify_by_email")
    list_filter = ("role",)


@admin.register(ProcessDocument)
class ProcessDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "process", "document_type", "published_at")
    list_filter = ("document_type",)


@admin.register(ParcelPhoto)
class ParcelPhotoAdmin(admin.ModelAdmin):
    list_display = ("process", "parcel_label", "captured_at")


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ("title", "process", "intervention_type", "performed_at")


@admin.register(ScheduledOperation)
class ScheduledOperationAdmin(admin.ModelAdmin):
    list_display = ("title", "process", "scheduled_start", "scheduled_end")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ("subject", "process", "updated_at")
    inlines = [MessageInline]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("membership", "notify_new_documents", "notify_upcoming_operations")


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("accessed_at", "user", "resource_type", "action")
    list_filter = ("resource_type", "action")
    readonly_fields = ("accessed_at",)

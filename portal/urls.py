from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("documents/", views.documents, name="documents"),
    path("photos/", views.photos, name="photos"),
    path("photos/<int:photo_id>/image/", views.photo_image, name="photo_image"),
    path("interventions/", views.interventions, name="interventions"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("messages/", views.messages, name="messages"),
    path("messages/send/", views.send_message, name="send_message"),
    path("security/", views.security_settings, name="security"),
    path(
        "security/notifications/",
        views.update_notifications,
        name="update_notifications",
    ),
    path(
        "documents/<int:document_id>/download/",
        views.document_download,
        name="document_download",
    ),
    path("files/signed/", views.signed_file, name="signed_file"),
]

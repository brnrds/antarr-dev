"""WorkOS AuthKit authentication views for Django."""

import hmac
import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from workos import WorkOSClient

logger = logging.getLogger(__name__)


def get_workos_client() -> WorkOSClient:
    """Get a configured WorkOS client instance."""
    return WorkOSClient(
        api_key=settings.WORKOS_API_KEY,
        client_id=settings.WORKOS_CLIENT_ID,
    )


def login_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Initiate the WorkOS AuthKit login flow.

    Redirects the user to WorkOS AuthKit for authentication.
    After successful authentication, WorkOS redirects back to the callback URL.
    """
    if request.session.get("workos_user"):
        return redirect("portal:dashboard")

    workos = get_workos_client()

    # Build the redirect URI for the callback
    redirect_uri = request.build_absolute_uri("/auth/callback/")
    oauth_state = secrets.token_urlsafe(32)
    request.session["workos_oauth_state"] = oauth_state

    # Generate the authorization URL
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit",
        redirect_uri=redirect_uri,
        state=oauth_state,
    )

    return redirect(authorization_url)


def callback_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Handle the OAuth callback from WorkOS AuthKit.

    Exchanges the authorization code for user information and creates a session.
    """
    # Get the authorization code from the callback
    code = request.GET.get("code")
    returned_state = request.GET.get("state")
    expected_state = request.session.pop("workos_oauth_state", None)

    state_is_valid = (
        expected_state
        and returned_state
        and hmac.compare_digest(returned_state, expected_state)
    )
    if not code or not state_is_valid:
        logger.warning("Rejected WorkOS callback with missing or invalid OAuth state")
        # If no code is present, redirect to home
        return redirect("/")

    try:
        workos = get_workos_client()

        # Exchange the code for user information
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
        )

        # Link the external identity to Django's authorization model. Users are
        # deliberately not granted access to a process here; internal staff do
        # that through ProcessMembership in the backoffice.
        user = auth_response.user
        User = get_user_model()
        django_user, _ = User.objects.get_or_create(
            email__iexact=user.email,
            defaults={
                "username": user.email,
                "email": user.email,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
            },
        )
        changed_fields = []
        for field, value in (
            ("email", user.email),
            ("first_name", user.first_name or ""),
            ("last_name", user.last_name or ""),
        ):
            if getattr(django_user, field) != value:
                setattr(django_user, field, value)
                changed_fields.append(field)
        if not django_user.has_usable_password():
            pass
        else:
            django_user.set_unusable_password()
            changed_fields.append("password")
        if changed_fields:
            django_user.save(update_fields=changed_fields)

        request.session.cycle_key()
        request.session["workos_user"] = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        request.session["portal_user_id"] = django_user.pk

    except Exception:
        logger.exception("WorkOS authentication failed")
        return redirect("workos_login")

    return redirect("portal:dashboard")


@require_POST
def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Log out the user by clearing the session.
    """
    # Clear WorkOS session data
    request.session.pop("workos_user", None)
    request.session.pop("portal_user_id", None)

    # Flush the entire session for a clean logout
    request.session.flush()

    return redirect("/")

"""
WorkOS AuthKit authentication views for Django.

These views handle the OAuth flow with WorkOS AuthKit:
- login_view: Redirects to WorkOS AuthKit for authentication
- callback_view: Handles the OAuth callback and creates a session
- logout_view: Clears the session and logs out
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from workos import WorkOSClient


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
    workos = get_workos_client()

    # Build the redirect URI for the callback
    redirect_uri = request.build_absolute_uri("/auth/callback/")

    # Generate the authorization URL
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit",
        redirect_uri=redirect_uri,
    )

    return redirect(authorization_url)


def callback_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Handle the OAuth callback from WorkOS AuthKit.

    Exchanges the authorization code for user information and creates a session.
    """
    workos = get_workos_client()

    # Get the authorization code from the callback
    code = request.GET.get("code")

    if not code:
        # If no code is present, redirect to home
        return redirect("/")

    try:
        # Exchange the code for user information
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
        )

        # Store user info in the session
        user = auth_response.user
        request.session["workos_user"] = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        # Store tokens for session management (optional, for refresh)
        if auth_response.access_token:
            request.session["workos_access_token"] = auth_response.access_token
        if auth_response.refresh_token:
            request.session["workos_refresh_token"] = auth_response.refresh_token

    except Exception as e:
        # Log the error and redirect to home on failure
        print(f"WorkOS authentication error: {e}")
        return redirect("/")

    return redirect("/")


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Log out the user by clearing the session.
    """
    # Clear WorkOS session data
    request.session.pop("workos_user", None)
    request.session.pop("workos_access_token", None)
    request.session.pop("workos_refresh_token", None)

    # Flush the entire session for a clean logout
    request.session.flush()

    return redirect("/")

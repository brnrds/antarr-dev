"""Authentication helpers for the landlord portal."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def require_portal_login(view_func: Callable) -> Callable:
    """
    Require either a WorkOS AuthKit session or a Django-authenticated user.

    The callback normally stores the linked Django user id in the session. The
    email fallback supports sessions created before that link was introduced.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        portal_user = request.user if request.user.is_authenticated else None
        workos_user = request.session.get("workos_user")

        if portal_user is None and workos_user:
            user_id = request.session.get("portal_user_id")
            filters = (
                {"pk": user_id} if user_id else {"email__iexact": workos_user["email"]}
            )
            portal_user = get_user_model().objects.filter(**filters).first()

        if portal_user is None:
            return redirect("workos_login")

        request.portal_user = portal_user
        return view_func(request, *args, **kwargs)

    return wrapper

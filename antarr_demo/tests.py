from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse


def _set_session_values(client, **values):
    session = client.session
    session.update(values)
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
class AuthCallbackTests(SimpleTestCase):
    @patch(
        "antarr_demo.auth_views.WorkOSClient",
        side_effect=AssertionError("WorkOS must not be initialized"),
    )
    def test_invalid_oauth_state_is_rejected_without_contacting_workos(self, _client):
        _set_session_values(self.client, workos_oauth_state="expected-state")

        response = self.client.get(
            reverse("workos_callback"),
            {"code": "authorization-code", "state": "wrong-state"},
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    @patch(
        "antarr_demo.auth_views.WorkOSClient",
        side_effect=RuntimeError("WorkOS is unavailable"),
    )
    def test_workos_initialization_failure_returns_to_login(self, _client):
        _set_session_values(self.client, workos_oauth_state="expected-state")

        response = self.client.get(
            reverse("workos_callback"),
            {"code": "authorization-code", "state": "expected-state"},
        )

        self.assertRedirects(
            response,
            reverse("workos_login"),
            fetch_redirect_response=False,
        )


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
class AuthLogoutTests(SimpleTestCase):
    def test_get_does_not_log_the_user_out(self):
        _set_session_values(
            self.client,
            workos_user={"id": "user_123", "email": "owner@example.com"},
        )

        response = self.client.get(reverse("workos_logout"))

        self.assertEqual(response.status_code, 405)
        self.assertIn("workos_user", self.client.session)

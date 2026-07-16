"""Shared pytest configuration for the antarr-demo project."""

import pytest


@pytest.fixture(autouse=True)
def _wagtail_site_settings(settings):
    """Ensure Wagtail admin base URL matches the test client."""
    settings.WAGTAILADMIN_BASE_URL = "http://testserver"

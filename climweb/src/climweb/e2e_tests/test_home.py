import pytest
from playwright.sync_api import Page, expect


@pytest.mark.playwright
def test_home_page_loads(page: Page):
    """Visit the home page and verify the page loads successfully.

    The Django development server is started by the ``django_server`` fixture in
    ``conftest.py``. Playwright connects to ``http://127.0.0.1:8001``.
    """
    response = page.goto("http://127.0.0.1:8001/")
    # Verify the page returned a successful HTTP status
    assert response.status < 400, f"Expected successful response, got {response.status}"
    # Basic sanity check – the page should contain the main navigation bar
    expect(page.locator("nav")).to_be_visible()


@pytest.mark.playwright
def test_admin_login_page_loads(page: Page):
    """Verify the Wagtail admin login page is accessible."""
    response = page.goto("http://127.0.0.1:8001/cms/")
    assert response.status < 400, f"Expected successful response, got {response.status}"
    # The admin login page should have a form
    expect(page.locator("form")).to_be_visible()

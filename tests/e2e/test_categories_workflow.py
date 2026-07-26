import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_categories_index_displays_category_grid(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/categories/")

    # Wait for category boxes to render via JS
    page.wait_for_selector(".category-box", timeout=5000)

    # Verify at least one category box is visible
    first_category = page.locator(".category-box").first
    expect(first_category).to_be_visible()

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on categories index: {page.js_errors}"


def test_category_detail_page_loads(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/categories/travel/")

    expect(page.locator("body")).to_be_visible()
    expect(page.get_by_role("heading", level=1)).to_be_visible()

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on category detail page: {page.js_errors}"

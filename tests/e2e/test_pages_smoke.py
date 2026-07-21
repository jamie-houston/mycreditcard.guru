import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_home_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/")
    
    # Assert HTTP success and main UI element exists
    expect(page.locator("body")).to_be_visible()
    
    # Assert zero uncaught JS page errors
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Home page: {page.js_errors}"


def test_cards_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/cards/")

    # Assert title or hero heading exists
    expect(page.locator("body")).to_be_visible()
    expect(page.get_by_role("heading", level=1)).to_be_visible()

    # Assert zero uncaught JS page errors
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Cards page: {page.js_errors}"


def test_profile_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/profile/")

    expect(page.locator("body")).to_be_visible()
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Profile page: {page.js_errors}"


def test_categories_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/categories/")

    expect(page.locator("body")).to_be_visible()
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Categories page: {page.js_errors}"


def test_help_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/help/")

    expect(page.locator("body")).to_be_visible()
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Help page: {page.js_errors}"


def test_resources_page_loads_without_js_errors(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/resources/")

    expect(page.locator("body")).to_be_visible()
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions on Resources page: {page.js_errors}"

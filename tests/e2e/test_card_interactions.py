import re
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_card_search_filters_results(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/cards/")

    page.wait_for_selector(".card-box", timeout=5000)

    search_input = page.locator("#searchCards")
    expect(search_input).to_be_visible()
    
    search_input.fill("Freedom")
    page.wait_for_timeout(300)
    
    freedom_card = page.get_by_text("Freedom", exact=False).first
    expect(freedom_card).to_be_visible()

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during search: {page.js_errors}"


def test_chip_filters_toggle_active_state(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/cards/")

    page.wait_for_selector(".card-box", timeout=5000)

    chip_nofee = page.locator("#chip-nofee")
    expect(chip_nofee).to_be_visible()

    chip_nofee.click()
    expect(chip_nofee).to_have_class(re.compile(r"\bactive\b"))

    chip_all = page.locator("#chip-all")
    chip_all.click()
    expect(chip_all).to_have_class(re.compile(r"\bactive\b"))

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during chip filter toggle: {page.js_errors}"


def test_more_filters_expand_panel(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/cards/")

    page.wait_for_selector(".card-box", timeout=5000)

    toggle = page.locator("#moreFiltersToggle")
    expect(toggle).to_be_visible()

    panel = page.locator("#moreFiltersPanel")
    expect(panel).to_be_hidden()

    toggle.click()
    expect(panel).to_be_visible()

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during panel expand: {page.js_errors}"

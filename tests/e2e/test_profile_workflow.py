import re
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_profile_tab_switching(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/profile/")

    # Switch to Best Card by Category tab
    tab_categories = page.locator("#tabBtnCategories")
    expect(tab_categories).to_be_visible()
    tab_categories.click()
    expect(tab_categories).to_have_class(re.compile(r"\bactive\b"))

    # Switch to Benefits & Credits tab
    tab_benefits = page.locator("#tabBtnBenefits")
    expect(tab_benefits).to_be_visible()
    tab_benefits.click()
    expect(tab_benefits).to_have_class(re.compile(r"\bactive\b"))

    # Switch back to My Cards tab
    tab_cards = page.locator("#tabBtnCards")
    tab_cards.click()
    expect(tab_cards).to_have_class(re.compile(r"\bactive\b"))

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during profile tab switching: {page.js_errors}"


def test_profile_settings_panel_toggle(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/profile/")

    # Settings toggle button
    settings_btn = page.locator(".settings-toggle-btn")
    expect(settings_btn).to_be_visible()

    settings_panel = page.locator("#settingsPanel")
    expect(settings_panel).to_be_hidden()

    # Click settings button to open settings panel
    settings_btn.click()
    expect(settings_panel).to_be_visible()

    # Toggle privacy radio buttons (Public vs Private)
    privacy_public = page.locator("#privacy-public")
    if privacy_public.is_visible():
        privacy_public.click()

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during settings panel toggle: {page.js_errors}"


def test_profile_segmented_filter_control(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/profile/")

    btn_business = page.locator("#btnProfileBusiness")
    expect(btn_business).to_be_visible()
    btn_business.click()
    expect(btn_business).to_have_class(re.compile(r"\bactive\b"))

    btn_all = page.locator("#btnProfileAll")
    btn_all.click()
    expect(btn_all).to_have_class(re.compile(r"\bactive\b"))

    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during segmented filter click: {page.js_errors}"

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_generate_roadmap_with_category_spending(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/roadmap/")

    # Ensure spending profile section is expanded
    spending_content = page.locator("#spendingProfileContent")
    if not spending_content.is_visible():
        page.locator("#spendingToggle").click()

    # Wait for category inputs to populate
    page.wait_for_selector("#spendingCategories input[type='number']", timeout=5000)

    # Fill $500 in first category spending input
    dining_input = page.locator("#spendingCategories input[type='number']").first
    dining_input.fill("500")

    # Click Get my roadmap
    get_roadmap_btn = page.locator("button", has_text="Get my roadmap")
    expect(get_roadmap_btn).to_be_visible()
    get_roadmap_btn.click()

    # Verify results section loads
    page.wait_for_selector("#results", timeout=10000)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during roadmap generation: {page.js_errors}"


def test_easy_mode_spending_input(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/roadmap/")

    if not page.locator("#spendingProfileContent").is_visible():
        page.locator("#spendingToggle").click()

    # Switch to Easy Mode
    btn_easy = page.locator("#btnModeEasy")
    expect(btn_easy).to_be_visible()
    btn_easy.click()

    # Verify Easy Mode input section displays
    easy_section = page.locator("#easyModeSpendingSection")
    expect(easy_section).to_be_visible()

    # Fill $3000 easy spending
    easy_input = page.locator("#easySpendingAmount")
    easy_input.fill("3000")

    # Click Get my roadmap
    get_roadmap_btn = page.locator("button", has_text="Get my roadmap")
    get_roadmap_btn.click()

    page.wait_for_selector("#results", timeout=10000)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions in Easy Mode: {page.js_errors}"


def test_upcoming_large_purchase_input(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/roadmap/")

    # Expand Upcoming large purchase collapsible section
    expense_toggle = page.locator("#expenseToggle")
    expect(expense_toggle).to_be_visible()
    expense_toggle.click()

    expense_content = page.locator("#expenseContent")
    expect(expense_content).to_be_visible()

    # Enter $5000 purchase amount
    expense_amount = page.locator("#expenseAmount")
    expense_amount.fill("5000")

    # Generate roadmap
    get_roadmap_btn = page.locator("button", has_text="Get my roadmap")
    get_roadmap_btn.click()

    page.wait_for_selector("#results", timeout=10000)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions in upcoming expense mode: {page.js_errors}"

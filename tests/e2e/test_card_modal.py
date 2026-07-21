import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def test_card_modal_opens_and_closes_cleanly(live_server, page_with_js_error_tracker):
    page = page_with_js_error_tracker
    page.goto(live_server.url + "/cards/")

    page.wait_for_selector(".card-box", timeout=5000)

    # Click card title/name to trigger openCardModal
    card_name = page.locator(".card-name").first
    expect(card_name).to_be_visible()
    card_name.click()

    # Verify modal opens
    modal = page.locator("#cardModal")
    expect(modal).to_be_visible()

    # Verify card title inside modal is populated
    modal_title = page.locator("#modalCardName")
    expect(modal_title).not_to_be_empty()

    # Click close button inside modal
    close_btn = modal.locator(".modal-close")
    close_btn.click()

    # Verify modal hides
    expect(modal).to_be_hidden()

    # Assert zero uncaught JS exceptions
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions during modal interaction: {page.js_errors}"

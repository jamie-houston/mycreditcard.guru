"""The confirm flow works with no Playwright dialog handler registered.

This is the point of story 10, stated as an assertion. **Deliberately no
`page.on("dialog")` anywhere in this file**: under the old `confirm()` the
click below would block on a native dialog Playwright never answers, and these
tests would hang until the timeout. That they run at all is the proof that
browser automation is unblocked.

`cards/test_no_native_dialogs.py` keeps the calls from coming back; this keeps
the replacement honest — a helper that renders but never resolves would pass
the grep guard and still be useless.
"""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db


def open_reset_confirm(page, live_server):
    """Fill a spending amount on /roadmap/, then click Reset All Data."""
    page.goto(live_server.url + "/roadmap/")

    if not page.locator("#spendingProfileContent").is_visible():
        page.locator("#spendingToggle").click()

    page.wait_for_selector("#spendingCategories input[type='number']", timeout=5000)
    spending_input = page.locator("#spendingCategories input[type='number']").first
    spending_input.fill("500")

    page.locator("button", has_text="Reset All Data").click()

    dialog = page.locator("[data-testid='confirm-dialog']")
    expect(dialog).to_be_visible()
    return spending_input, dialog


def test_confirm_dialog_accept_runs_the_action(live_server, authenticated_page):
    page = authenticated_page
    spending_input, dialog = open_reset_confirm(page, live_server)

    page.locator("[data-testid='confirm-dialog-accept']").click()

    expect(dialog).to_have_count(0)
    expect(spending_input).to_have_value("")
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_confirm_dialog_cancel_leaves_the_data_alone(live_server, authenticated_page):
    page = authenticated_page
    spending_input, dialog = open_reset_confirm(page, live_server)

    page.locator("[data-testid='confirm-dialog-cancel']").click()

    expect(dialog).to_have_count(0)
    expect(spending_input).to_have_value("500")
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_escape_dismisses_the_dialog_as_a_cancel(live_server, authenticated_page):
    page = authenticated_page
    spending_input, dialog = open_reset_confirm(page, live_server)

    page.keyboard.press("Escape")

    expect(dialog).to_have_count(0)
    expect(spending_input).to_have_value("500")


def test_prompt_dialog_resolves_the_typed_value(live_server, authenticated_page):
    """promptDialog() round-trips a value back to the caller.

    Driven straight through the helper rather than through the rename-member
    flow, which needs a saved household entity; what's under test is the helper
    resolving, and the rename caller is one `await` away from this.
    """
    page = authenticated_page
    page.goto(live_server.url + "/roadmap/")

    # Statement body, not an expression: page.evaluate() awaits a returned
    # promise, and awaiting this one here would block before anything can click.
    page.evaluate("() => { window.__dialogResult = promptDialog('Rename to:', 'Lisa'); }")
    expect(page.locator("[data-testid='confirm-dialog']")).to_be_visible()

    entry = page.locator("[data-testid='confirm-dialog-input']")
    expect(entry).to_have_value("Lisa")
    entry.fill("Lisa Houston")
    page.locator("[data-testid='confirm-dialog-accept']").click()

    assert page.evaluate("() => window.__dialogResult") == "Lisa Houston"


def test_prompt_dialog_cancel_resolves_null(live_server, authenticated_page):
    page = authenticated_page
    page.goto(live_server.url + "/roadmap/")

    # Statement body, not an expression: page.evaluate() awaits a returned
    # promise, and awaiting this one here would block before anything can click.
    page.evaluate("() => { window.__dialogResult = promptDialog('Rename to:', 'Lisa'); }")
    expect(page.locator("[data-testid='confirm-dialog']")).to_be_visible()

    page.locator("[data-testid='confirm-dialog-cancel']").click()

    assert page.evaluate("() => window.__dialogResult") is None

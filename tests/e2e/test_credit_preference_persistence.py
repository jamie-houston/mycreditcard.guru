import io
import os

import pytest
from django.conf import settings
from django.core.management import call_command
from playwright.sync_api import expect

from cards.models import (
    SpendingCredit,
    UserSpendingCreditPreference,
    UserSpendingProfile,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def seed_spending_credits(db):
    """The shared conftest seeds system data through `import_cards`, which has
    no notion of spending credits — those have their own command and their own
    JSON. Without them the roadmap form renders no credit checkboxes at all,
    so every locator in this file times out.
    """
    if not SpendingCredit.objects.exists():
        call_command(
            "import_spending_credits",
            file=os.path.join(settings.BASE_DIR, "data/input/system/spending_credits.json"),
            stdout=io.StringIO(),
        )


def _expand_spending(page):
    if not page.locator("#spendingProfileContent").is_visible():
        page.locator("#spendingToggle").click()
    page.wait_for_selector("#spendingCategories input[type='number']", timeout=10000)


def _generate(page):
    # Generating flips the page to the Results tab, which hides the whole
    # builder — button and credit checkboxes with it. Regenerating by hand
    # means coming back to Settings first, which is the path Jamie's repro
    # walks and the reason a second plain click times out.
    builder = page.locator("#roadmapBuilder")
    if not builder.is_visible():
        page.locator("#tabRoadmapSettings").click()
        expect(builder).to_be_visible()
    page.locator("button", has_text="Get my roadmap").click()
    # getRecommendations() settles into results mode only once the response has
    # rendered, and that hides the builder. #results is already in the DOM by
    # the second call and the loading placeholder is too transient to catch, so
    # this is the only stable end state to wait on.
    expect(builder).to_be_hidden(timeout=30000)


def test_credit_enabled_in_card_modal_survives_regenerate(live_server, authenticated_page):
    """Jamie's repro: enable a benefit in a card modal, regenerate, and the
    benefit is off again. The modal's per-slug PUT was correct; the form
    checkbox never re-read it, and the Generate request then sent that stale
    snapshot as the complete set of valued credits.
    """
    page = authenticated_page
    # loadSavedData() syncs the credit checkboxes from the server on a 500 ms
    # timer after load (roadmap.js:913). Left unwaited, that GET lands *after*
    # the modal write below and ticks the checkbox for a reason that has
    # nothing to do with the fix — which is exactly how an earlier draft of
    # this test passed against the unfixed code.
    with page.expect_response(
        lambda r: "/cards/credit-preferences/" in r.url and r.request.method == "GET"
    ):
        page.goto(live_server.url + "/roadmap/")
    _expand_spending(page)

    checkbox = page.locator("input[name='spending_credit_preferences']").first
    page.wait_for_selector("input[name='spending_credit_preferences']", timeout=10000)
    slug = checkbox.get_attribute("value")
    expect(checkbox).not_to_be_checked()

    page.locator("#spendingCategories input[type='number']").first.fill("500")
    _generate(page)

    # What the card modal's checkbox does — the modal itself is opened from the
    # results, but the write path under test is this one call.
    page.evaluate("(slug) => toggleModalCreditUsage(slug, true)", slug)

    # The form checkbox must now agree with what the modal just saved.
    expect(checkbox).to_be_checked()

    _generate(page)

    expect(checkbox).to_be_checked()
    profile = UserSpendingProfile.objects.get(user__username="testuser")
    assert UserSpendingCreditPreference.objects.filter(
        profile=profile, spending_credit__slug=slug, values_credit=True
    ).exists(), f"preference for {slug} did not survive regenerating the roadmap"
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"

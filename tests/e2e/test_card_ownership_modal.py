"""Story 11 regression cover for the two /cards/ ownership bugs the manual
passes found. Both are state-carried-between-opens bugs, so each test asserts
on the *first* interaction of a fresh page — a reload is what used to hide them.
"""
import pytest
from django.contrib.auth.models import User
from playwright.sync_api import expect

from cards.models import CreditCard, UserCard

pytestmark = pytest.mark.django_db

SUBMIT = "#cardOwnershipForm button[type='submit']"


def test_edit_details_submit_label_before_any_save(live_server, authenticated_page):
    """Bug D: the submit label was only ever set in saveCardOwnership's finally,
    so before the first save of a session it showed the template default."""
    user = User.objects.get(username="testuser")
    card = CreditCard.objects.filter(is_active=True).first()
    UserCard.objects.create(user=user, card=card)

    page = authenticated_page
    page.goto(live_server.url + "/cards/")
    page.wait_for_selector(".card-box.owned", timeout=5000)

    owned = page.locator(".card-box.owned").first
    owned.get_by_role("button", name="Edit card details").click()

    expect(page.locator(SUBMIT)).to_have_text("Save Details")
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_adding_a_card_updates_the_browse_page_without_reload(live_server, authenticated_page):
    """Bug B: refreshPageDisplay hit filterCards, which re-renders from an
    allCards whose hasCard flags were computed once at load — so the box
    redrew unowned until a reload."""
    page = authenticated_page
    page.goto(live_server.url + "/cards/")
    page.wait_for_selector(".card-box", timeout=5000)

    add_button = page.get_by_role("button", name="I have this card").first
    target = page.locator(".card-box").filter(has=add_button).first
    card_name = target.locator(".card-name").inner_text()

    add_button.click()
    expect(page.locator(SUBMIT)).to_have_text("Add Card")
    page.locator(SUBMIT).click()

    owned = page.locator(".card-box.owned").filter(has_text=card_name).first
    expect(owned.locator(".card-box-owned-chip")).to_be_visible(timeout=5000)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"

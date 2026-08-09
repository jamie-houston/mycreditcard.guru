"""Removing a card always asks first.

Story 10 replaced the 14 native dialogs that existed; it could not add the one
that didn't. `removeLastCardModal` — the card detail modal's "Remove from my
cards" — dropped the card the instant it was clicked, which is what Jamie hit
answering `[dialog-stacks-over-cardmodal]`. The same gap was in
`toggleCardOwnership`'s remove direction (`/categories/<slug>/`) and in
`removeCardOwnership` (roadmap results).

The cancel case is the one that matters: a confirm that renders but doesn't
actually gate the removal would pass a visibility-only assertion, so both tests
assert on the `UserCard` row's state, not on the dialog. Per story 07 removal
is a *soft close* — the row survives and gains a `closed_date` — so "removed"
here means closed, not deleted.
"""
import pytest
from django.contrib.auth.models import User
from playwright.sync_api import expect

from cards.models import CreditCard, UserCard

pytestmark = pytest.mark.django_db

DIALOG = "[data-testid='confirm-dialog']"


def is_open(user, card):
    """True while the holding is still open — removal soft-closes it."""
    return UserCard.objects.filter(
        user=user, card=card, closed_date__isnull=True).exists()


def open_owned_card_modal(page, live_server):
    """Seed one owned card, open /cards/, and open its detail modal."""
    user = User.objects.get(username="testuser")
    card = CreditCard.objects.filter(is_active=True).first()
    UserCard.objects.create(user=user, card=card)

    page.goto(live_server.url + "/cards/")
    page.wait_for_selector(".card-box.owned", timeout=5000)

    owned = page.locator(".card-box.owned").first
    owned.get_by_role("button", name="View Details").click()

    remove = page.locator("#modalOwnershipButton")
    expect(remove).to_have_text("❌ Remove from my cards", timeout=5000)
    return user, card, remove


def test_modal_remove_asks_before_dropping_the_card(live_server, authenticated_page):
    page = authenticated_page
    user, card, remove = open_owned_card_modal(page, live_server)

    remove.click()

    expect(page.locator(DIALOG)).to_be_visible()
    assert is_open(user, card), "the card was removed before the confirm was answered"

    page.locator("[data-testid='confirm-dialog-accept']").click()

    expect(page.locator("#modalOwnershipButton")).to_have_text(
        "✅ I have this card", timeout=5000)
    assert not is_open(user, card)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_cancelling_the_modal_remove_keeps_the_card(live_server, authenticated_page):
    page = authenticated_page
    user, card, remove = open_owned_card_modal(page, live_server)

    remove.click()
    page.locator("[data-testid='confirm-dialog-cancel']").click()

    expect(page.locator(DIALOG)).to_have_count(0)
    expect(page.locator("#modalOwnershipButton")).to_have_text(
        "❌ Remove from my cards")
    assert is_open(user, card)
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_the_confirm_renders_above_the_card_modal(live_server, authenticated_page):
    """The stacking half of `[dialog-stacks-over-cardmodal]`: the dialog is
    z-index 10000 against `.modal`'s 2000, and its Escape handler runs in the
    capture phase, so dismissing it must leave #cardModal open."""
    page = authenticated_page
    _, _, remove = open_owned_card_modal(page, live_server)

    remove.click()
    expect(page.locator(DIALOG)).to_be_visible()

    dialog_z, modal_z = page.evaluate(
        """() => [
            getComputedStyle(document.querySelector("[data-testid='confirm-dialog']")).zIndex,
            getComputedStyle(document.getElementById('cardModal')).zIndex,
        ]"""
    )
    assert int(dialog_z) > int(modal_z), f"dialog {dialog_z} not above modal {modal_z}"

    page.keyboard.press("Escape")

    expect(page.locator(DIALOG)).to_have_count(0)
    expect(page.locator("#cardModal")).to_be_visible()

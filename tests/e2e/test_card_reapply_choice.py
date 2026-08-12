"""Story 13: re-applying for a closed card must ask which reading is meant
(new holding vs. fixing the old record) instead of silently reopening the
stale row. Assert on the model rows, not on the choice UI being visible,
per CLAUDE.md's destructive-actions e2e rule (same principle applies here:
the choice UI showing is necessary but not sufficient — the write is what
matters)."""
import pytest
from django.contrib.auth.models import User
from playwright.sync_api import expect

from cards.models import CreditCard, UserCard

pytestmark = pytest.mark.django_db


def test_reapply_choice_creates_a_second_open_holding(live_server, authenticated_page):
    user = User.objects.get(username="testuser")
    card = CreditCard.objects.filter(is_active=True).first()
    closed = UserCard.objects.create(
        user=user, card=card, opened_date="2021-01-01", closed_date="2022-01-01")

    page = authenticated_page
    page.goto(live_server.url + "/cards/")
    page.wait_for_selector(".card-box", timeout=5000)

    target = page.locator(".card-box").filter(has_text=card.name).first
    target.get_by_role("button", name="I have this card").click()

    expect(page.locator("#cardReapplyChoice")).to_be_visible(timeout=5000)
    expect(page.locator("#cardOwnershipFields")).to_be_hidden()
    page.get_by_role("button", name="I re-applied for this card").click()

    page.fill("#opened_date", "2026-08-01")
    page.locator("#cardOwnershipForm button[type='submit']").click()

    expect(page.locator(".card-box.owned").filter(has_text=card.name)).to_be_visible(timeout=5000)

    rows = UserCard.objects.filter(user=user, card=card).order_by("opened_date")
    assert rows.count() == 2
    assert rows[0].id == closed.id
    assert rows[0].closed_date is not None
    assert rows[1].closed_date is None
    assert str(rows[1].opened_date) == "2026-08-01"
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"


def test_fix_the_record_choice_reopens_the_same_row(live_server, authenticated_page):
    user = User.objects.get(username="testuser")
    card = CreditCard.objects.filter(is_active=True).first()
    closed = UserCard.objects.create(
        user=user, card=card, opened_date="2021-01-01", closed_date="2022-01-01")

    page = authenticated_page
    page.goto(live_server.url + "/cards/")
    page.wait_for_selector(".card-box", timeout=5000)

    target = page.locator(".card-box").filter(has_text=card.name).first
    target.get_by_role("button", name="I have this card").click()

    expect(page.locator("#cardReapplyChoice")).to_be_visible(timeout=5000)
    page.get_by_role("button", name="Fix the existing record").click()

    expect(page.locator("#opened_date")).to_have_value("2021-01-01")
    page.locator("#cardOwnershipForm button[type='submit']").click()

    expect(page.locator(".card-box.owned").filter(has_text=card.name)).to_be_visible(timeout=5000)

    rows = UserCard.objects.filter(user=user, card=card)
    assert rows.count() == 1
    closed.refresh_from_db()
    assert closed.closed_date is None
    assert len(page.js_errors) == 0, f"Uncaught JS exceptions: {page.js_errors}"

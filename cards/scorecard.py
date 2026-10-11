"""Card scorecard: is each open card paying for its annual fee in credits?

Display only — the roadmap engine never reads credit usage. Every number on
the page comes from three inputs: CreditCard.annual_fee, the card's statement
credits, and the UserCreditUsage rows recorded against them.

"Used (12 mo)" counts every usage period that OVERLAPS (today - 365d, today],
including the period still in progress. Jamie chose this on 2026-10-11 over
"periods that ended in the window", which drops this year's annual credits
and the current quarter. The known cost: an annual credit used in two
calendar years can show twice in one 12-month view.

Earn edge — the rewards a card earns over a no-fee card — is deliberately not
counted; it needs a per-card allocation of the spending profile.
"""
from datetime import date, timedelta

from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import ProfileEntity, UserCard, UserSpendingProfile

STATEMENT_CREDIT_TYPES = {'', 'statement_credit'}
NEAR_BREAK_EVEN = 100  # dollars below zero that still reads as "close"


def period_bounds(period_key):
    """(first day, last day) of a CardCredit.get_period_key key."""
    year = int(period_key[:4])
    suffix = period_key[5:]
    if not suffix:
        return date(year, 1, 1), date(year, 12, 31)
    if suffix.startswith('Q'):
        first_month, months = (int(suffix[1]) - 1) * 3 + 1, 3
    elif suffix.startswith('H'):
        first_month, months = (int(suffix[1]) - 1) * 6 + 1, 6
    else:
        first_month, months = int(suffix), 1
    start = date(year, first_month, 1)
    after = first_month + months
    end = (date(year + 1, 1, 1) if after > 12 else date(year, after, 1)) - timedelta(days=1)
    return start, end


def next_fee_date(opened_date, today):
    """The opened_date anniversary on or after today (None if unknown)."""
    if opened_date is None:
        return None
    for year in (today.year, today.year + 1):
        try:
            anniversary = opened_date.replace(year=year)
        except ValueError:  # Feb 29 in a non-leap year
            anniversary = date(year, 2, 28)
        if anniversary >= today:
            return anniversary


def credit_name(card_credit):
    if card_credit.description:
        return card_credit.description
    if card_credit.spending_credit:
        return card_credit.spending_credit.display_name
    if card_credit.category:
        return f'{card_credit.category.display_name} Credit'
    return 'Credit'


def verdict(net):
    if net >= 0:
        return 'pays'
    if net >= -NEAR_BREAK_EVEN:
        return 'close'
    return 'short'


def build_scorecard(user, today):
    """One row per open card, plus household totals."""
    window_start = today - timedelta(days=365)
    profile = UserSpendingProfile.objects.filter(user=user).first()
    usages = {}
    if profile:
        for usage in profile.credit_usages.filter(used=True):
            usages.setdefault(usage.card_credit_id, []).append(usage)

    holdings = (UserCard.objects
                .filter(user=user, closed_date__isnull=True)
                .select_related('card', 'owner')
                .order_by('card__name', F('opened_date').asc(nulls_last=True), 'id'))

    rows = []
    usage_shown_on = {}  # card id -> the holding whose row carries its usage
    for holding in holdings:
        card = holding.card
        # Usage is recorded per household, not per holding, so a card held
        # twice shows its usage once rather than counting it on both rows.
        shared_with = usage_shown_on.get(card.id)
        if shared_with is None:
            usage_shown_on[card.id] = holding

        credits = [c for c in card.credits.filter(is_active=True)
                   .select_related('spending_credit', 'category')
                   if c.offer_type in STATEMENT_CREDIT_TYPES]
        available = used = 0.0
        unused = []
        for card_credit in credits:
            available += card_credit.annual_value
            period_value = card_credit.annual_value / card_credit.times_per_year
            if shared_with is not None:
                continue
            current_key = card_credit.get_period_key(today)
            used_now = 0.0
            for usage in usages.get(card_credit.id, []):
                amount = (float(usage.amount_used) if usage.amount_used is not None
                          else period_value)
                start, end = period_bounds(usage.period_key)
                if start <= today and end > window_start:
                    used += amount
                if usage.period_key == current_key:
                    used_now = amount
            left = period_value - used_now
            if left > 0.005:
                unused.append({'name': credit_name(card_credit), 'left': left,
                               'period': current_key})

        fee = float(card.annual_fee)
        net = used - fee
        unused.sort(key=lambda u: -u['left'])
        gap_closers, running = [], 0.0
        if net < 0:
            for credit in unused:
                if running >= -net:
                    break
                gap_closers.append(credit)
                running += credit['left']

        rows.append({
            'holding': holding,
            'card': card,
            'owner': holding.owner.name if holding.owner else '',
            'fee': fee,
            'next_fee': next_fee_date(holding.opened_date, today) if fee else None,
            'available': available,
            'used': used,
            'net': net,
            'verdict': verdict(net),
            'unused': unused,
            'gap_closers': gap_closers,
            'gap_closed': running >= -net,
            'usage_shown_on': shared_with if credits else None,
        })

    totals = {
        'fees': sum(r['fee'] for r in rows),
        'used': sum(r['used'] for r in rows),
        'net': sum(r['net'] for r in rows),
    }
    return rows, totals


def scorecard_view(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('account_login')}?next={request.path}")

    today = date.today()
    rows, totals = build_scorecard(request.user, today)
    rows.sort(key=lambda r: (r['net'], r['card'].name))
    show_owner = ProfileEntity.objects.filter(profile__user=request.user).count() > 1
    return render(request, 'scorecard.html', {
        'rows': rows, 'totals': totals, 'today': today, 'show_owner': show_owner,
    })

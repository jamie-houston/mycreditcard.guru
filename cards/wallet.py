"""Phone-first wallet view: which owned card to use for each category today.

Deliberately independent of the recommendation engine — this answers
"which card do I swipe?" from owned cards' reward rates alone, so it
stays fast and trivially verifiable.
"""

from datetime import date

from django.shortcuts import redirect, render
from django.urls import reverse

from .models import UserCard, UserSpendingProfile

# Category slugs that represent the unboosted base/catch-all rate.
BASE_CATEGORY_SLUGS = {'other', 'general'}


def quarter_end(on_date):
    """Last day of the calendar quarter containing on_date."""
    quarter = (on_date.month - 1) // 3 + 1
    last_month = quarter * 3
    if last_month == 12:
        return date(on_date.year, 12, 31)
    return date(on_date.year, last_month + 1, 1).replace(day=1) - date.resolution


def build_wallet_rows(user, today=None):
    """Return (rows, base_entry) for the user's open cards.

    rows: one entry per spending category where an owned card beats the
    best base rate, sorted by the user's monthly spending (desc), then rate.
    base_entry: the best catch-all card for everything else.
    """
    today = today or date.today()

    user_cards = (
        UserCard.objects
        .filter(user=user, closed_date__isnull=True)
        .select_related('card', 'card__issuer')
    )

    best_by_category = {}
    base_entry = None
    for user_card in user_cards:
        reward_categories = (
            user_card.card.reward_categories
            .active_on(today)
            .select_related('category', 'reward_type')
        )
        for rc in reward_categories:
            entry = {
                'card': user_card.card,
                'card_label': user_card.display_name,
                'category': rc.category,
                'rate': rc.reward_rate,
                'reward_type': rc.reward_type.name,
                'end_date': rc.end_date,
                'is_rotating': rc.end_date is not None,
                'max_annual_spend': rc.max_annual_spend,
            }
            if rc.category.slug in BASE_CATEGORY_SLUGS:
                if base_entry is None or rc.reward_rate > base_entry['rate']:
                    base_entry = entry
            else:
                current = best_by_category.get(rc.category_id)
                if current is None or rc.reward_rate > current['rate']:
                    best_by_category[rc.category_id] = entry

    # A category row only earns its place if it beats the base card.
    base_rate = base_entry['rate'] if base_entry else 0
    rows = [e for e in best_by_category.values() if e['rate'] > base_rate]

    spending = {}
    profile = UserSpendingProfile.objects.filter(user=user).first()
    if profile:
        for amount in profile.spending_amounts.select_related('category'):
            spending[amount.category_id] = amount.monthly_amount

    for row in rows:
        row['monthly_spending'] = spending.get(row['category'].id)

    rows.sort(
        key=lambda r: (
            -(r['monthly_spending'] or 0),
            -r['rate'],
            r['category'].sort_order,
        )
    )
    return rows, base_entry


def wallet_view(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('account_login')}?next={request.path}")

    today = date.today()
    rows, base_entry = build_wallet_rows(request.user, today)
    open_card_count = UserCard.objects.filter(
        user=request.user, closed_date__isnull=True
    ).count()

    context = {
        'rows': rows,
        'base_entry': base_entry,
        'open_card_count': open_card_count,
        'today': today,
        'quarter': (today.month - 1) // 3 + 1,
        'quarter_end': quarter_end(today),
    }
    return render(request, 'wallet.html', context)

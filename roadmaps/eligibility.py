"""
Issuer eligibility rules: like strategy presets, a rule is data, not code.

Two distinct rule types (research + sources in docs/PROJECT_STATUS.md, S3):

- Application rules (ISSUER_RULES[slug]['application_rules']): can the user
  get approved for a new card from this issuer at all. A blocked card is
  silently excluded from apply recommendations — the roadmap simply picks
  the next-best card.

- Bonus rules (issuer-level 'bonus_rule' default, overridable per card via
  metadata['bonus_eligibility']): the user can get the card, but the signup
  bonus won't pay out. The engine still considers the card for ongoing value
  and scores signup_bonus = $0, with a short note surfaced on the
  recommendation ("bonus unlikely — ...").

Both are evaluated against the user's FULL card history, including closed
cards (5/24 counts since-closed cards; Amex's lifetime rule outlives
cancellation). When a bonus-earned date is unknown it's approximated as
opened_date + BONUS_EARN_APPROX_MONTHS; a prior card with no dates at all is
treated as bonus-earned-recently — better to undersell a bonus than to
promise one the issuer will refuse. `UserCard.bonus_override=False` (user
says they never actually earned that prior card's bonus — referred, never
activated) excludes it from these prior-bonus checks entirely; `True` or
`None` (infer from rules) behaves as before.

Card metadata keys understood here:
  metadata['bonus_eligibility'] = {
      'once_per_lifetime': true,      # bonus once ever for this card
      'months_since_bonus': 24,       # no bonus if one was earned in window
      'family': 'southwest-personal', # prior-bonus checks scan cards sharing
                                      # this family, not just this exact card
      'label': 'Southwest 24-month rule',  # shown in the UI note
  }
  metadata['application_family'] = 'southwest-personal'
      # currently holding any OPEN card in this family blocks applying
  metadata['application_eligibility'] = {
      'once_per_lifetime': true,      # can never apply again once ever held
      'family': 'chase-sapphire-personal',  # scans cards sharing this family
                                             # (open OR closed), not just this
                                             # exact card
      'label': 'Chase Sapphire application rule',  # shown in the block reason
  }
      # Distinct from application_family above: application_family only
      # blocks while a family card is OPEN; application_eligibility blocks
      # forever, even after the prior card is closed (Phase K, per-entity —
      # see application_block's ISSUER_RULES-driven max_open_cards rule too).

An issuer's 'application_rules' entries come in two shapes: a window rule
('max_new_cards' + 'period_months'/'period_days') counts cards OPENED in
that window; a cap rule ('max_open_cards') counts cards currently OPEN,
uncapped by time (e.g. Amex's 5-card limit) — both keyed on 'counts' (see
_counts_toward).

Known-unmodeled gaps (Phase M verification, 2026-07-19 — deliberately out
of scope, not bugs): no aggregate cross-issuer open-card cap; Amex's
5-card rule is one flat counter (doesn't split charge vs. credit or
business vs. personal sub-limits issuers sometimes apply); no cross-issuer
new-account velocity throttle. If one of these becomes a real complaint,
add a new ISSUER_RULES shape (or a household-wide rule alongside it) here.
"""

import calendar
from datetime import date, timedelta

# When a UserCard has no bonus_earned_date, assume the bonus landed about
# this long after opening (typical 3-month spending requirement).
BONUS_EARN_APPROX_MONTHS = 3

ISSUER_RULES = {
    'chase': {
        # 5/24: >=5 personal cards (any issuer, incl. closed) opened in 24
        # months -> denied. Business cards don't count UNLESS their issuer
        # reports business cards to personal credit (Capital One, Discover,
        # TD). Chase business applications are still subject to the rule.
        'application_rules': [
            {'rule': '5/24', 'max_new_cards': 5, 'period_months': 24,
             'counts': 'all_issuers_personal'},
        ],
        # Sapphire lifetime bonuses are per-card metadata, not issuer-wide.
    },
    'bank-of-america': {
        # 2/3/4: max 2 new BofA cards per 30 days, 3 per 12 months,
        # 4 per 24 months. Only BofA's own cards count.
        'application_rules': [
            {'rule': '2/30', 'max_new_cards': 2, 'period_days': 30,
             'counts': 'same_issuer'},
            {'rule': '3/12', 'max_new_cards': 3, 'period_months': 12,
             'counts': 'same_issuer'},
            {'rule': '4/24', 'max_new_cards': 4, 'period_months': 24,
             'counts': 'same_issuer'},
        ],
    },
    'capital-one': {
        # One new Capital One card per 6 months, personal + business pooled.
        'application_rules': [
            {'rule': '1/6mo', 'max_new_cards': 1, 'period_months': 6,
             'counts': 'same_issuer'},
        ],
        # Most C1 business cards report to personal credit -> they count
        # toward Chase 5/24.
        'business_reports_to_personal': True,
    },
    'american-express': {
        # Once-per-lifetime, per card (not per family). Pop-up jail is
        # unmodelable noise; prior ownership is the signal we act on.
        'bonus_rule': {'once_per_lifetime': True,
                       'label': 'Amex once-per-lifetime rule'},
        # Amex caps how many cards you can hold open at once (Phase K).
        'application_rules': [
            {'rule': '5-card-limit', 'max_open_cards': 5,
             'counts': 'same_issuer'},
        ],
    },
    'citi': {
        # No bonus if you earned THAT card's bonus in the past 48 months
        # (per-card since 2025; clock runs from bonus receipt).
        'bonus_rule': {'months_since_bonus': 48,
                       'label': 'Citi 48-month rule'},
    },
    'discover': {
        'business_reports_to_personal': True,
    },
    'td-bank': {
        'business_reports_to_personal': True,
    },
}


def _issuer_rules(slug):
    return ISSUER_RULES.get(slug, {})


def months_before(today, months):
    """Calendar-accurate `months` before `today` (clamped to month end).

    The old 5/24 check used 24*30 days, which drifts ~19 days over the
    window — enough to mis-classify a card opened near the boundary.
    """
    total = today.year * 12 + (today.month - 1) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _counts_toward(counts, user_card, candidate_card):
    """Does this history entry count against the given window rule?"""
    if counts == 'same_issuer':
        return user_card.card.issuer_id == candidate_card.issuer_id
    if counts == 'all_issuers_personal':
        if user_card.card.card_type == 'personal':
            return True
        # Business cards count only when the issuer reports them to
        # personal credit.
        return bool(_issuer_rules(user_card.card.issuer.slug).get(
            'business_reports_to_personal'))
    raise ValueError(f"Unknown application-rule counts scope: {counts!r}")


def application_block(card, card_history, today):
    """Why the user can't be approved for `card`, or None if they can.

    `card_history` is every card the user has held — open AND closed —
    with opened_date/closed_date (UserCard rows or equivalent mocks).
    """
    for rule in _issuer_rules(card.issuer.slug).get('application_rules', []):
        if 'max_open_cards' in rule:
            count = sum(
                1 for uc in card_history
                if uc.closed_date is None
                and _counts_toward(rule['counts'], uc, card)
            )
            if count >= rule['max_open_cards']:
                return (f"{card.issuer.name} {rule['rule']} rule: already "
                        f"holds {count} open cards")
            continue

        if 'period_months' in rule:
            window_start = months_before(today, rule['period_months'])
        else:
            window_start = today - timedelta(days=rule['period_days'])
        count = sum(
            1 for uc in card_history
            if uc.opened_date and uc.opened_date >= window_start
            and _counts_toward(rule['counts'], uc, card)
        )
        if count >= rule['max_new_cards']:
            return (f"{card.issuer.name} {rule['rule']} rule: {count} cards "
                    f"opened since {window_start:%b %Y}")

    # Family blocks: e.g. holding any open Southwest personal card blocks
    # applying for another one.
    family = (card.metadata or {}).get('application_family')
    if family:
        for uc in card_history:
            if uc.closed_date is not None or uc.card.id == card.id:
                continue
            if (uc.card.metadata or {}).get('application_family') == family:
                return (f"holding {uc.card.name} blocks new "
                        f"{family.replace('-', ' ')} applications")

    # Once-per-lifetime application rules (e.g. Chase Sapphire): unlike the
    # family block above, this checks the FULL history (open or closed) —
    # having ever held a card in the family blocks applying again, forever.
    app_elig = (card.metadata or {}).get('application_eligibility') or {}
    if app_elig.get('once_per_lifetime'):
        elig_family = app_elig.get('family')
        label = app_elig.get('label') or f"{card.name} application rules"
        if elig_family:
            prior = [uc for uc in card_history
                     if ((uc.card.metadata or {}).get('application_eligibility') or {})
                     .get('family') == elig_family]
        else:
            prior = [uc for uc in card_history if uc.card.id == card.id]
        if prior:
            return f"can't reapply — {label} (once per lifetime)"
    return None


def _approx_bonus_earned_date(user_card):
    """Best guess at when this card's signup bonus was earned.

    Explicit bonus_earned_date wins; otherwise opened_date + ~3 months;
    None means we know nothing (caller treats that as recent).
    """
    explicit = getattr(user_card, 'bonus_earned_date', None)
    if explicit:
        return explicit
    if user_card.opened_date:
        return user_card.opened_date + timedelta(
            days=BONUS_EARN_APPROX_MONTHS * 30)
    return None


def bonus_ineligibility(card, card_history, today):
    """Why `card`'s signup bonus should be valued at $0, or None if it's
    (as far as we can tell) earnable. The returned string is user-facing."""
    rule = dict(_issuer_rules(card.issuer.slug).get('bonus_rule') or {})
    rule.update((card.metadata or {}).get('bonus_eligibility') or {})
    if not rule:
        return None

    family = rule.get('family')
    if family:
        prior = [uc for uc in card_history
                 if ((uc.card.metadata or {}).get('bonus_eligibility') or {})
                 .get('family') == family]
    else:
        prior = [uc for uc in card_history if uc.card.id == card.id]
    # bonus_override=False is the user telling us they never actually earned
    # that prior card's bonus (referred, never activated) — it must not
    # block a new one. override=True/None (infer from rules) still counts.
    prior = [uc for uc in prior if getattr(uc, 'bonus_override', None) is not False]
    if not prior:
        return None

    label = rule.get('label') or f"{card.issuer.name} bonus rules"

    if rule.get('once_per_lifetime'):
        return f"bonus unlikely — you've had this card before ({label})"

    months = rule.get('months_since_bonus')
    if months:
        cutoff = months_before(today, int(months))
        for uc in prior:
            earned = _approx_bonus_earned_date(uc)
            if earned is None or earned >= cutoff:
                which = ('this card' if uc.card.id == card.id
                         else uc.card.name)
                return (f"bonus unlikely — you earned {which}'s bonus "
                        f"within the last {months} months ({label})")
    return None

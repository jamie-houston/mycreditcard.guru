"""Phase I: minimal curated redemption guidance.

Display-only — nothing here feeds engine math or the reconciliation guard
(line items + signup bonus - fee = headline). Deliberately a small
hand-curated dict, not a new model/migration: transfer-partner and
redemption-portal data changes rarely enough that a schema would be
premature maintenance surface, especially with an engine-cleanup pass
planned soon. Extend REDEMPTION_GUIDANCE as more points_program values get
curated in data/input/cards/*.json (today: chase_ultimate_rewards,
amex_membership_rewards only, per CLAUDE.md's Points pooling section).
"""

REDEMPTION_GUIDANCE = {
    'chase_ultimate_rewards': {
        'program_label': 'Chase Ultimate Rewards',
        'portal_url': 'https://www.chase.com/personal/credit-cards/ultimate-rewards',
        # Dollars per point, same convention as metadata.reward_value_multiplier
        # (_own_multiplier) — NOT cents. 0.015 = 1.5 cents/point.
        'value_per_point': 0.015,
        'transfer_partners': [
            'United MileagePlus', 'Southwest Rapid Rewards', 'World of Hyatt',
            'Marriott Bonvoy', 'British Airways Executive Club', 'Air Canada Aeroplan',
        ],
        'note': ('Best value transferring to airline/hotel partners or booking travel '
                  'through the Chase portal (Sapphire Reserve/Preferred or Ink Business '
                  'Preferred cardholders get the boosted portal rate).'),
    },
    'amex_membership_rewards': {
        'program_label': 'Amex Membership Rewards',
        'portal_url': 'https://global.americanexpress.com/rewards/membershiprewards',
        'value_per_point': 0.01,
        'transfer_partners': [
            'Delta SkyMiles', 'British Airways Executive Club', 'Air Canada Aeroplan',
            'Air France-KLM Flying Blue', 'Marriott Bonvoy', 'Hilton Honors',
        ],
        'note': ('Best value transferring to airline/hotel partners; Pay With Points '
                  'and Amex Travel redemptions run well below that.'),
    },
}

_CASHBACK_NOTE = ('Redeem as a statement credit or direct deposit — no transfer step, '
                    'no portal to route through.')
_GENERIC_NOTE = ("Check the issuer's rewards portal for redemption options — no "
                   'transfer-partner data curated for this card yet.')


def redemption_guidance_for(card):
    """Redemption guidance for one card.

    Curated when the card's metadata.points_program matches a program in
    REDEMPTION_GUIDANCE; a generic fallback otherwise, branching only on
    whether the card earns cashback vs. points/miles. Always returns the
    same shape so the frontend never has to branch on missing keys.
    """
    points_program = (card.metadata or {}).get('points_program')
    curated = REDEMPTION_GUIDANCE.get(points_program)
    if curated:
        return {
            'program_label': curated['program_label'],
            'portal_url': curated['portal_url'],
            'value_per_point': curated['value_per_point'],
            'transfer_partners': curated['transfer_partners'],
            'note': curated['note'],
        }

    reward_type_name = card.primary_reward_type.name.lower() if card.primary_reward_type_id else ''
    note = _CASHBACK_NOTE if reward_type_name == 'cashback' else _GENERIC_NOTE

    return {
        'program_label': None,
        'portal_url': card.url or None,
        'value_per_point': None,
        'transfer_partners': [],
        'note': note,
    }

"""Phase I / Decoupling: minimal curated redemption guidance from database.

Display-only — nothing here feeds engine math or the reconciliation guard
(line items + signup bonus - fee = headline).
"""

from cards.models import PointsProgram, PointsValuation

_CASHBACK_NOTE = ('Redeem as a statement credit or direct deposit — no transfer step, '
                    'no portal to route through.')
_GENERIC_NOTE = ("Check the issuer's rewards portal for redemption options — no "
                   'transfer-partner data curated for this card yet.')

# Code-level fallback curated values for the two main programs, in case the database isn't fully seeded (e.g. in tests)
_CHASE_UR_FALLBACK = {
    'program_label': 'Chase Ultimate Rewards',
    'portal_url': 'https://www.chase.com/personal/credit-cards/ultimate-rewards',
    'value_per_point': 0.015,
    'transfer_partners': [
        'United MileagePlus', 'Southwest Rapid Rewards', 'World of Hyatt',
        'Marriott Bonvoy', 'British Airways Executive Club', 'Air Canada Aeroplan',
    ],
    'note': ('Best value transferring to airline/hotel partners or booking travel '
              'through the Chase portal (Sapphire Reserve/Preferred or Ink Business '
              'Preferred cardholders get the boosted portal rate).'),
}

_AMEX_MR_FALLBACK = {
    'program_label': 'Amex Membership Rewards',
    'portal_url': 'https://global.americanexpress.com/rewards/membershiprewards',
    'value_per_point': 0.01,
    'transfer_partners': [
        'Delta SkyMiles', 'British Airways Executive Club', 'Air Canada Aeroplan',
        'Air France-KLM Flying Blue', 'Marriott Bonvoy', 'Hilton Honors',
    ],
    'note': ('Best value transferring to airline/hotel partners; Pay With Points '
              'and Amex Travel redemptions run well below that.'),
}


def redemption_guidance_for(card, user=None):
    """Redemption guidance for one card.

    Curated when the card has an associated PointsProgram in the database,
    otherwise falls back to metadata, and then falls back to generic notes.
    """
    points_program = card.points_program
    
    # Fallback to metadata for robustness
    if not points_program and card.metadata and 'points_program' in card.metadata:
        program_slug = card.metadata['points_program']
        if program_slug:
            points_program = PointsProgram.objects.filter(slug=program_slug).first()

    if points_program:
        fallback = None
        if points_program.slug == 'chase_ultimate_rewards':
            fallback = _CHASE_UR_FALLBACK
        elif points_program.slug == 'amex_membership_rewards':
            fallback = _AMEX_MR_FALLBACK

        # 1. Look up valuation (custom user override vs system-default)
        val = None
        if user and user.is_authenticated:
            val = PointsValuation.objects.filter(points_program=points_program, user=user).first()
        if not val:
            val = PointsValuation.objects.filter(points_program=points_program, user=None).first()
        
        # 2. Get value_per_point
        if val:
            value_per_point = float(val.value)
        else:
            value_per_point = fallback['value_per_point'] if fallback else 0.01

        # 3. Get transfer partners and notes (prefer DB if non-empty, otherwise fallback)
        transfer_partners = points_program.transfer_partners
        if not transfer_partners and fallback:
            transfer_partners = fallback['transfer_partners']
            
        note = points_program.note
        if not note and fallback:
            note = fallback['note']
            
        portal_url = points_program.portal_url
        if not portal_url and fallback:
            portal_url = fallback['portal_url']
            
        name = points_program.name
        if fallback and (not name or name == points_program.slug.replace('_', ' ').title()):
            name = fallback['program_label']

        return {
            'program_label': name,
            'portal_url': portal_url,
            'value_per_point': value_per_point,
            'transfer_partners': transfer_partners or [],
            'note': note,
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

"""Shared dollars-per-point valuation helpers.

Resolves a `PointsProgram`'s dollar-per-point rate (user override -> system
default), and maps a `CardCredit.currency` string (e.g. 'SOUTHWEST') to a
program via `PointsProgram.currency_code` so points-denominated credits can
be discounted to real redemption worth instead of counted at face value.

Used by `roadmaps/engine/calculators/credits.py` (the engine valuation
chokepoint) and `CardCredit.annual_value` (display/admin convenience).
`roadmaps/redemption.py` has its own inline lookup for reward-earning
redemption guidance (display-only) — not routed through here to keep this
change scoped to credit valuation.
"""
import logging

from cards.models import PointsProgram, PointsValuation

logger = logging.getLogger(__name__)

# Conservative safety net for a non-USD currency with no seeded PointsProgram.
# Deliberately low (never the raw face value) so an unmapped currency degrades
# safely instead of silently re-inflating a credit's value.
UNMAPPED_CURRENCY_RATE = 0.01


def value_per_point(program, user=None):
    """Dollars per point for a PointsProgram: user override -> system default -> None."""
    val = None
    if user and getattr(user, 'is_authenticated', False):
        val = PointsValuation.objects.filter(points_program=program, user=user).first()
    if not val:
        val = PointsValuation.objects.filter(points_program=program, user=None).first()
    return float(val.value) if val else None


def credit_currency_rate(currency, user=None):
    """Dollars per unit for a CardCredit.currency. USD/blank -> 1.0.

    Looks up a PointsProgram by `currency_code`; if found, uses its valuation
    (user override -> system default). Falls back to UNMAPPED_CURRENCY_RATE
    (with a warning) for any non-USD currency without a seeded program.
    """
    if not currency or currency.upper() == 'USD':
        return 1.0
    program = PointsProgram.objects.filter(currency_code=currency).first()
    if program:
        vpp = value_per_point(program, user)
        if vpp is not None:
            return vpp
    logger.warning(
        "No valuation for credit currency %r; defaulting to %s/pt",
        currency, UNMAPPED_CURRENCY_RATE,
    )
    return UNMAPPED_CURRENCY_RATE

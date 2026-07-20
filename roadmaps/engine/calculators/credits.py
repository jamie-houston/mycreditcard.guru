import logging
from typing import List
from cards.models import CreditCard
from cards.valuations import credit_currency_rate
from ..utils import info_item

logger = logging.getLogger(__name__)

class CreditsCalculator:
    """
    Manages benefit preference matching, individual card credit valuations,
    and portfolio credit allocation / deduplication.
    """

    def __init__(self, engine):
        self.engine = engine
        self._currency_rate_cache = {}

    def _currency_rate(self, currency: str) -> float:
        """Dollars per unit for a credit's currency, memoized per-engine so hot
        optimizer loops don't re-query PointsValuation. 1.0 for USD/blank."""
        cached = self._currency_rate_cache.get(currency)
        if cached is not None:
            return cached
        rate = credit_currency_rate(currency, getattr(self.engine.profile, 'user', None))
        self._currency_rate_cache[currency] = rate
        return rate

    def counted_card_credits(self, card: CreditCard) -> list:
        """Credits on this card that count for THIS user."""
        cached = self.engine._card_credits_cache.get(card.id)
        if cached is not None:
            return cached

        if self.engine._credit_prefs is None:
            prefs = set()
            if hasattr(self.engine.profile, 'spending_credit_preferences'):
                prefs = set(
                    pref.spending_credit.slug
                    for pref in self.engine.profile.spending_credit_preferences.filter(values_credit=True)
                )
            self.engine._credit_prefs = prefs
            self.engine._credit_spending_categories = set(
                spending.category.slug
                for spending in self.engine.profile.spending_amounts.all()
                if spending.monthly_amount > 0
            )

        entries = []
        for card_credit in card.credits.filter(is_active=True).select_related(
                'spending_credit', 'category'):
            if card_credit.spending_credit and card_credit.spending_credit.slug in self.engine._credit_prefs:
                credit_type = "benefit"
                credit_name = card_credit.spending_credit.display_name
                dedup_key = card_credit.spending_credit.slug
                stackable = card_credit.spending_credit.stackable
            elif card_credit.category and card_credit.category.slug in self.engine._credit_spending_categories:
                credit_type = "category"
                credit_name = f"{card_credit.category.display_name} Credit"
                dedup_key = f"category_{card_credit.category.slug}"
                stackable = True
            else:
                continue

            currency = card_credit.currency or 'USD'
            is_usd = currency.upper() == 'USD'
            rate = 1.0 if is_usd else self._currency_rate(currency)
            value = float(card_credit.value)
            annual_value = value * card_credit.times_per_year * rate

            frequency_text = ""
            if card_credit.times_per_year > 1:
                if is_usd:
                    frequency_text = f" (${value:.0f} × {card_credit.times_per_year}/year)"
                else:
                    frequency_text = (f" ({value:,.0f} {currency} pts × "
                                       f"{card_credit.times_per_year}/year → ${annual_value:.0f})")

            entries.append({
                'name': credit_name or card_credit.description,
                'value': value,
                'times_per_year': card_credit.times_per_year,
                'annual_value': annual_value,
                'type': credit_type,
                'description': card_credit.description,
                'frequency_display': frequency_text,
                'dedup_key': dedup_key,
                'stackable': stackable,
                'currency': currency,
                'is_usd': is_usd,
                'rate': rate,
            })

        self.engine._card_credits_cache[card.id] = entries
        return entries

    def calculate_card_credits_value(self, card: CreditCard) -> tuple[float, list]:
        """Single-card credit value with NO portfolio context."""
        entries = self.counted_card_credits(card)
        return sum(e['annual_value'] for e in entries), entries

    @staticmethod
    def credit_breakdown_item(credit: dict) -> dict:
        """Breakdown line for a counted credit (same shape as reward lines).

        USD credits render the face `$` value throughout. Points-denominated
        credits (non-USD `currency`) render the point amount and per-point
        rate alongside the discounted dollar total, so the line item still
        reconciles to the dollars that flow into totals (trustworthy math)."""
        is_usd = credit.get('is_usd', True)
        if is_usd:
            if credit['times_per_year'] > 1:
                credit_display = f"{credit['name']} (${credit['value']:.0f}×{credit['times_per_year']})"
            else:
                credit_display = f"{credit['name']} (${credit['value']:.0f})"
            calculation = f"Card benefit: ${credit['annual_value']:.0f} annually"
        else:
            currency = credit['currency']
            qty_text = f"{credit['value']:,.0f} {currency} pts"
            if credit['times_per_year'] > 1:
                qty_text += f" × {credit['times_per_year']}/year"
                credit_display = f"{credit['name']} ({credit['value']:,.0f} {currency} pts×{credit['times_per_year']} → ${credit['annual_value']:.0f})"
            else:
                credit_display = f"{credit['name']} ({credit['value']:,.0f} {currency} pts → ${credit['annual_value']:.0f})"
            calculation = f"Card benefit: {qty_text} × ${credit['rate']:.4f}/pt → ${credit['annual_value']:.0f} annually"
        return {
            'category_name': credit_display,
            'monthly_spend': 0,
            'annual_spend': 0,
            'reward_rate': 0,
            'reward_multiplier': 1.0,
            'points_earned': credit['annual_value'],
            'category_rewards': credit['annual_value'],
            'calculation': calculation,
            'type': 'credit',
            'credit_detail': credit,
        }

    def allocate_portfolio_credits(self, cards: List[CreditCard]) -> dict:
        """Portfolio-wide credit allocation — the single dedup authority."""
        values = {}
        items = {}
        non_stackable = {}  # dedup_key -> {card_id: {'card', 'entries', 'total'}}
        for card in cards:
            if card.id in values:
                continue
            values[card.id] = 0.0
            items[card.id] = []
            for entry in self.counted_card_credits(card):
                if entry['stackable']:
                    values[card.id] += entry['annual_value']
                    items[card.id].append(self.credit_breakdown_item(entry))
                else:
                    carrier = non_stackable.setdefault(entry['dedup_key'], {}).setdefault(
                        card.id, {'card': card, 'entries': [], 'total': 0.0})
                    carrier['entries'].append(entry)
                    carrier['total'] += entry['annual_value']

        for carriers in non_stackable.values():
            winner = max(carriers.values(),
                         key=lambda c: (c['total'], -c['card'].id))
            for carrier in carriers.values():
                card_id = carrier['card'].id
                if carrier is winner:
                    for entry in carrier['entries']:
                        values[card_id] += entry['annual_value']
                        items[card_id].append(self.credit_breakdown_item(entry))
                else:
                    name = carrier['entries'][0]['name']
                    items[card_id].append(info_item(
                        f"{name} (counted once)",
                        f"{name} doesn't stack across cards — "
                        f"counted once, on {winner['card'].name}"))

        return {card_id: (values[card_id], items[card_id]) for card_id in values}

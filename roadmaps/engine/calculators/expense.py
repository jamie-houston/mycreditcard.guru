import logging
from typing import List
from cards.models import CreditCard, SpendingCategory

logger = logging.getLogger(__name__)


class ExpenseRecommender:
    """
    Phase N: one-off upcoming-expense mode. Given a single lump-sum amount
    (optionally tagged with a spending category), ranks which card to APPLY
    for to cover it (signup-bonus minimum-spend fit + category rate − fee)
    and which card the user already OWNS is best to put it on (category rate
    only). Deliberately a separate, parallel path from the portfolio engine
    (`RewardsCalculator`/`BonusCapacityManager`'s portfolio-allocation
    methods) — a one-time amount doesn't belong in `spending_amounts`
    (monthly, annualized everywhere), and this recommender's value for each
    card is a simple visible sum:

        value_for_expense = signup_bonus_value + category_rewards - effective_annual_fee

    which reconciles by construction, so it can't regress the portfolio
    reconciliation guard it never touches.

    Uses each card's OWN reward multiplier only (no points-pooling) — same
    pragmatic scope choice already made for the other summary/legacy paths
    (`RewardsCalculator.calculate_card_rewards_breakdown`,
    `_calculate_portfolio_summary`). The signup bonus valuation still pools
    against currently-held cards (via `program_multipliers`), matching the
    established Phase J behavior for bonuses.
    """

    MAX_RESULTS_CAP = 5

    def __init__(self, engine):
        self.engine = engine

    def recommend_for_expense(self, amount: float, category_slug: str,
                               eligible_cards: List[CreditCard],
                               max_results: int = 5) -> dict:
        amount = float(amount)
        category_name, parent_slug = self._resolve_category(category_slug)

        program_multipliers = self.engine._program_multipliers(
            [uc.card for uc in self.engine.user_cards])

        owned_card_ids = {uc.card.id for uc in self.engine.user_cards}
        apply_candidates = []
        for card in eligible_cards:
            if card.id in owned_card_ids:
                continue
            if not self.engine._is_eligible_for_card(card):
                continue
            apply_candidates.append(self._score_apply_candidate(
                card, amount, category_slug, parent_slug, program_multipliers))

        apply_candidates.sort(key=lambda c: c['value_for_expense'], reverse=True)
        limit = max(1, min(int(max_results or 1), self.MAX_RESULTS_CAP))

        best_owned = None
        best_owned_value = 0.0
        for uc in self.engine.user_cards:
            category_rewards, rate, _ = self._category_rewards_for_expense(
                uc.card, amount, category_slug, parent_slug)
            if best_owned is None or category_rewards > best_owned_value:
                best_owned_value = category_rewards
                best_owned = {
                    'card': uc.card,
                    'action': 'keep',
                    'signup_bonus_value': 0.0,
                    'category_rewards': category_rewards,
                    'effective_annual_fee': 0.0,
                    'value_for_expense': category_rewards,
                    'reward_rate': rate,
                    'bonus_note': '',
                }

        return {
            'amount': amount,
            'category_slug': category_slug,
            'category_name': category_name,
            'apply': apply_candidates[:limit],
            'best_owned': best_owned,
        }

    def _score_apply_candidate(self, card: CreditCard, amount: float,
                                category_slug: str, parent_slug: str,
                                program_multipliers: dict) -> dict:
        category_rewards, rate, _ = self._category_rewards_for_expense(
            card, amount, category_slug, parent_slug)

        bonus_manager = self.engine.bonus_capacity_manager
        reachable, required_amount, time_months = \
            bonus_manager.can_meet_signup_requirement_with_expense(card, amount)
        signup_bonus_value = bonus_manager.get_signup_bonus_value_for_expense(
            card, amount, program_multipliers)

        annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
        effective_annual_fee = 0.0 if annual_fee_waived else float(card.annual_fee)

        value_for_expense = signup_bonus_value + category_rewards - effective_annual_fee

        bonus_note = ''
        if card.signup_bonus_amount:
            bonus_note = self._bonus_note(amount, reachable, required_amount, time_months)

        return {
            'card': card,
            'action': 'apply',
            'signup_bonus_value': signup_bonus_value,
            'category_rewards': category_rewards,
            'effective_annual_fee': effective_annual_fee,
            'value_for_expense': value_for_expense,
            'reward_rate': rate,
            'bonus_note': bonus_note,
        }

    def _category_rewards_for_expense(self, card: CreditCard, amount: float,
                                       category_slug: str, parent_slug: str) -> tuple:
        """(dollar rewards, best matching rate, own multiplier) for spending
        `amount` on `card`. Matches the highest specific-category rate up to
        its `max_annual_spend` cap, spilling any remainder to the card's
        base rate — same cap-then-spill shape as
        `RewardsCalculator.calculate_portfolio_allocation`, applied to a
        single lump instead of a portfolio allocation.
        """
        base_slugs = self.engine.rewards_calculator.BASE_CATEGORY_SLUGS
        active = card.reward_categories.active_on(self.engine.today).select_related('category')

        specific = []
        base = []
        for rc in active:
            if rc.category.slug in base_slugs:
                base.append(rc)
            elif category_slug and (rc.category.slug == category_slug
                                     or (parent_slug and rc.category.slug == parent_slug)):
                specific.append(rc)
        specific.sort(key=lambda rc: float(rc.reward_rate), reverse=True)
        base.sort(key=lambda rc: float(rc.reward_rate), reverse=True)

        multiplier = self.engine._own_multiplier(card)
        remaining = amount
        total_rewards = 0.0
        best_rate = 0.0
        for rc in specific + base:
            if remaining <= 0:
                break
            take = remaining
            if rc.max_annual_spend:
                take = min(take, float(rc.max_annual_spend))
            if take <= 0:
                continue
            rate = float(rc.reward_rate)
            total_rewards += take * rate * multiplier
            if best_rate == 0.0:
                best_rate = rate
            remaining -= take

        return total_rewards, best_rate, multiplier

    @staticmethod
    def _resolve_category(category_slug: str) -> tuple:
        if not category_slug:
            return 'General purchase', None
        try:
            category = SpendingCategory.objects.select_related('parent').get(slug=category_slug)
            name = category.display_name or category.name
            parent_slug = category.parent.slug if category.parent else None
            return name, parent_slug
        except SpendingCategory.DoesNotExist:
            return category_slug.replace('_', ' ').title(), None

    @staticmethod
    def _bonus_note(amount: float, reachable: bool, required_amount: float,
                     time_months: float) -> str:
        if required_amount <= 0:
            return ''
        if reachable:
            return (f"Your ${amount:,.0f} purchase covers the "
                     f"${required_amount:,.0f} minimum spend in "
                     f"{time_months:.0f} months")
        return (f"Doesn't reach the ${required_amount:,.0f} minimum spend in "
                f"{time_months:.0f} months — bonus not counted")

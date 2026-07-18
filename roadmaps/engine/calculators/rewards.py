import logging
from typing import List, Dict
from cards.models import CreditCard, SpendingCategory

logger = logging.getLogger(__name__)

class RewardsCalculator:
    """
    Manages spending allocations, points pooling effective multipliers,
    parent category spending rollups, and card rewards breakdowns.
    """

    BASE_CATEGORY_SLUGS = ('general', 'other', 'everything-else')

    def __init__(self, engine):
        self.engine = engine

    def total_monthly_spending(self) -> float:
        return sum(float(amount) for amount in self.engine.spending_amounts.values())

    def own_multiplier(self, card: CreditCard) -> float:
        """This card's own points/miles value, ignoring any points program it belongs to."""
        return float(card.metadata.get('reward_value_multiplier', 0.01))

    def program_multipliers(self, portfolio_cards: List[CreditCard]) -> dict:
        """{points_program slug: best own multiplier among held cards in that program}."""
        best = {}
        for c in portfolio_cards or []:
            program = (c.metadata or {}).get('points_program')
            if not program:
                continue
            best[program] = max(best.get(program, 0.0), self.own_multiplier(c))
        return best

    def program_best_cards(self, portfolio_cards: List[CreditCard]) -> dict:
        """{points_program slug: the held card achieving that program's best multiplier}."""
        best = {}
        for c in portfolio_cards or []:
            program = (c.metadata or {}).get('points_program')
            if not program:
                continue
            current = best.get(program)
            if current is None or self.own_multiplier(c) > self.own_multiplier(current):
                best[program] = c
        return best

    def effective_multiplier(self, card: CreditCard, program_multipliers: dict = None) -> float:
        """A card's points are worth whatever the best redemption card in the SAME points program can get."""
        own = self.own_multiplier(card)
        program = (card.metadata or {}).get('points_program')
        if not program or not program_multipliers:
            return own
        return max(own, program_multipliers.get(program, 0.0))

    def build_parent_category_spending(self) -> dict:
        """Build parent category spending by aggregating subcategory spending."""
        all_spending = {}
        for category_slug, monthly_amount in self.engine.spending_amounts.items():
            all_spending[category_slug] = float(monthly_amount) * 12

        parent_category_spending = {}
        parent_categories_with_subcategories = set()

        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory and annual_spend > 0:
                    parent_categories_with_subcategories.add(spending_category.parent.slug)
            except SpendingCategory.DoesNotExist:
                pass

        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    if category_slug in parent_categories_with_subcategories:
                        pass
                    else:
                        parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend

        return parent_category_spending

    def calculate_portfolio_allocation(self, portfolio_cards: List[CreditCard]) -> list:
        """Allocate the user's annual spending across the portfolio."""
        seen_ids = set()
        cards = []
        for card in portfolio_cards:
            if card.id not in seen_ids:
                seen_ids.add(card.id)
                cards.append(card)

        category_rewards = []
        base_rewards = []
        for card in cards:
            active = card.reward_categories.active_on(self.engine.today).select_related(
                'category', 'category__parent')
            for reward_cat in active:
                if reward_cat.category.slug in self.BASE_CATEGORY_SLUGS:
                    base_rewards.append((card, reward_cat))
                else:
                    category_rewards.append((card, reward_cat))

        cap_room = {}
        for _, reward_cat in category_rewards + base_rewards:
            if reward_cat.max_annual_spend:
                cap_room[reward_cat.id] = float(reward_cat.max_annual_spend)

        base_rewards.sort(key=lambda cr: float(cr[1].reward_rate), reverse=True)

        allocation = []

        def allocate(spending_slug, category_name, amount, candidates):
            remaining = amount
            for card, reward_cat in candidates:
                if remaining <= 0:
                    return
                take = remaining
                if reward_cat.id in cap_room:
                    take = min(take, cap_room[reward_cat.id])
                    if take <= 0:
                        continue
                    cap_room[reward_cat.id] -= take
                allocation.append({
                    'category_slug': spending_slug,
                    'category_name': category_name,
                    'card': card,
                    'rate': float(reward_cat.reward_rate),
                    'annual_spend': take,
                    'max_spend': float(reward_cat.max_annual_spend) if reward_cat.max_annual_spend else None,
                    'reward_category_id': reward_cat.id,
                    'is_base_rate': reward_cat.category.slug in self.BASE_CATEGORY_SLUGS,
                })
                remaining -= take
            if remaining > 0:
                allocation.append({
                    'category_slug': spending_slug,
                    'category_name': category_name,
                    'card': None,
                    'rate': 0.0,
                    'annual_spend': remaining,
                    'max_spend': None,
                    'reward_category_id': None,
                    'is_base_rate': False,
                })

        for spending_slug, monthly_amount in self.engine.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            if annual_spend <= 0:
                continue

            parent_slug = None
            try:
                spend_category = SpendingCategory.objects.select_related('parent').get(slug=spending_slug)
                category_name = spend_category.display_name or spend_category.name
                if spend_category.parent:
                    parent_slug = spend_category.parent.slug
            except SpendingCategory.DoesNotExist:
                category_name = spending_slug.replace('_', ' ').title()

            matches = [
                (card, reward_cat) for card, reward_cat in category_rewards
                if reward_cat.category.slug == spending_slug
                or (parent_slug and reward_cat.category.slug == parent_slug)
            ]
            candidates = sorted(matches + base_rewards, key=lambda cr: float(cr[1].reward_rate), reverse=True)
            allocate(spending_slug, category_name, annual_spend, candidates)

        return allocation

    def calculate_card_annual_rewards(self, card: CreditCard) -> float:
        """Calculate annual rewards for a card based on user spending."""
        breakdown = self.calculate_card_rewards_breakdown(card)
        return breakdown['total_rewards']

    def calculate_card_allocated_breakdown(self, card: CreditCard, portfolio_allocation: list,
                                            credit_allocation: dict,
                                            program_multipliers: dict = None) -> dict:
        """Breakdown for one card using only the spending allocated to it."""
        total_rewards = 0.0
        breakdown_details = []
        reward_value_multiplier = self.effective_multiplier(card, program_multipliers)

        for entry in portfolio_allocation:
            if entry['card'] is None or entry['card'].id != card.id:
                continue
            annual_spend = entry['annual_spend']
            if annual_spend <= 0:
                continue
            rate = entry['rate']
            points_earned = annual_spend * rate
            category_rewards = points_earned * reward_value_multiplier
            total_rewards += category_rewards

            breakdown_details.append({
                'category_name': f"{entry['category_name']} ({rate:.1f}x)",
                'monthly_spend': annual_spend / 12,
                'annual_spend': annual_spend,
                'reward_rate': rate,
                'reward_multiplier': reward_value_multiplier,
                'points_earned': points_earned,
                'category_rewards': category_rewards,
                'calculation': f"${annual_spend:,.0f} × {rate:.1f}x × {reward_value_multiplier:.3f} = ${category_rewards:.2f}",
                'type': 'reward_category',
            })

        credits_value, credit_items = credit_allocation.get(card.id, (0.0, []))
        total_rewards += credits_value
        breakdown_details.extend(credit_items)

        total_spending_on_card = sum(
            item['annual_spend'] for item in breakdown_details
            if item['type'] == 'reward_category'
        )

        return {
            'total_rewards': total_rewards,
            'breakdown': breakdown_details,
            'total_spending_on_card': total_spending_on_card,
            'reward_multiplier': reward_value_multiplier,
        }

    def calculate_card_rewards_breakdown(self, card: CreditCard) -> dict:
        """Calculate detailed rewards breakdown for a card (standalone path)."""
        total_rewards = 0.0
        breakdown_details = []
        reward_value_multiplier = self.own_multiplier(card)

        all_spending = {}
        for category_slug, monthly_amount in self.engine.spending_amounts.items():
            all_spending[category_slug] = float(monthly_amount) * 12

        parent_category_spending = self.build_parent_category_spending()
        allocated_spending = 0.0

        for reward_category in card.reward_categories.active_on(self.engine.today):
            category_slug = reward_category.category.slug
            annual_spend = parent_category_spending.get(category_slug, 0.0)

            if annual_spend > 0:
                if reward_category.max_annual_spend:
                    annual_spend = min(annual_spend, float(reward_category.max_annual_spend))

                allocated_spending += annual_spend
                reward_rate = float(reward_category.reward_rate)
                points_earned = annual_spend * reward_rate
                category_rewards = points_earned * float(reward_value_multiplier)
                total_rewards += category_rewards

                category_display_name = reward_category.category.display_name or reward_category.category.name
                category_with_multiplier = f"{category_display_name} ({reward_rate:.1f}x)"

                breakdown_details.append({
                    'category_name': category_with_multiplier,
                    'monthly_spend': annual_spend / 12,
                    'annual_spend': annual_spend,
                    'reward_rate': reward_rate,
                    'reward_multiplier': float(reward_value_multiplier),
                    'points_earned': points_earned,
                    'category_rewards': category_rewards,
                    'calculation': f"${annual_spend:,.0f} × {reward_rate:.1f}x × {float(reward_value_multiplier):.3f} = ${category_rewards:.2f}",
                    'type': 'reward_category'
                })

        unallocated_spending = sum(parent_category_spending.values()) - allocated_spending
        if unallocated_spending > 0:
            general_category = card.reward_categories.filter(
                is_active=True,
                category__slug__in=['general', 'other', 'everything-else']
            ).first()

            if general_category:
                reward_rate = float(general_category.reward_rate)
                points_earned = unallocated_spending * reward_rate
                category_rewards = points_earned * float(reward_value_multiplier)
                total_rewards += category_rewards

                other_category_with_multiplier = f"Other Spending ({reward_rate:.1f}x)"

                breakdown_details.append({
                    'category_name': other_category_with_multiplier,
                    'monthly_spend': unallocated_spending / 12,
                    'annual_spend': unallocated_spending,
                    'reward_rate': reward_rate,
                    'reward_multiplier': float(reward_value_multiplier),
                    'points_earned': points_earned,
                    'category_rewards': category_rewards,
                    'calculation': f"${unallocated_spending:,.0f} × {reward_rate:.1f}x × {float(reward_value_multiplier):.3f} = ${category_rewards:.2f}",
                    'type': 'reward_category'
                })

        credits_value, credits_breakdown = self.engine._calculate_card_credits_value(card)
        total_rewards += credits_value
        for credit in credits_breakdown:
            breakdown_details.append(self.engine._credit_breakdown_item(credit))

        total_spending_on_card = sum(
            item['annual_spend'] for item in breakdown_details
            if item['type'] == 'reward_category'
        )

        return {
            'total_rewards': total_rewards,
            'breakdown': breakdown_details,
            'total_spending_on_card': total_spending_on_card,
            'reward_multiplier': float(reward_value_multiplier)
        }

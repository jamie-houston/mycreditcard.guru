import logging
from typing import List, Dict
from cards.models import CreditCard
from collections import defaultdict
from itertools import combinations

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Manages portfolio search combinations, scenario evaluations, greedy card selection,
    and efficiency calculations to select the optimal portfolio.
    """

    def __init__(self, engine):
        self.engine = engine

    def find_optimal_portfolio(self, current_cards: List[CreditCard], available_cards: List[CreditCard], max_cards: int) -> List[dict]:
        """Find the optimal combination of cards for maximum portfolio value."""
        scenarios = []

        # Scenario 1: Keep profitable ones, add best new cards
        profitable_current_cards = []
        unprofitable_current_cards = []
        for card in current_cards:
            rewards_breakdown = self.engine._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            net_value = annual_rewards - annual_fee

            if net_value >= 0 or annual_fee == 0:
                profitable_current_cards.append(card)
            else:
                unprofitable_current_cards.append((card, annual_rewards, annual_fee))

        scenario1 = self.evaluate_portfolio_scenario(
            cards_to_keep=profitable_current_cards,
            cards_to_apply=[],
            available_cards=available_cards,
            max_total_cards=max_cards
        )

        for card, annual_rewards, annual_fee in unprofitable_current_cards:
            scenario1['actions'].append({
                'card': card,
                'action': 'cancel',
                'reasoning': f"Cancel - losing money: ${annual_rewards:.0f} rewards vs ${annual_fee} fee (net: ${annual_rewards - annual_fee:.0f})",
                'priority': 1
            })

        scenarios.append(("keep_profitable_add_new", scenario1))

        # Scenario 2: Full optimization
        scenario2 = self.evaluate_portfolio_scenario(
            cards_to_keep=[],
            cards_to_apply=current_cards + available_cards,
            available_cards=[],
            max_total_cards=max_cards
        )
        scenarios.append(("full_optimization", scenario2))

        logger.debug(f"Scenario comparison:")
        for name, scenario in scenarios:
            actions_summary = {}
            for action in scenario['actions']:
                action_type = action['action']
                actions_summary[action_type] = actions_summary.get(action_type, 0) + 1
            logger.debug(f"  {name}: value=${scenario['net_portfolio_value']:.2f}, actions={actions_summary}")

        best_scenario = max(scenarios, key=lambda x: x[1]['net_portfolio_value'])
        logger.debug(f"Selected scenario: {best_scenario[0]} with value ${best_scenario[1]['net_portfolio_value']:.2f}")
        return best_scenario[1]['actions']

    def evaluate_portfolio_scenario(self, cards_to_keep: List[CreditCard], cards_to_apply: List[CreditCard],
                                   available_cards: List[CreditCard], max_total_cards: int) -> dict:
        """Evaluate a specific portfolio scenario and return optimized actions."""
        if not cards_to_keep and cards_to_apply:
            return self.select_optimal_card_combination(cards_to_apply, max_total_cards)
        else:
            actions = []
            for card in cards_to_keep:
                rewards_breakdown = self.engine._calculate_card_rewards_breakdown(card)
                annual_rewards = rewards_breakdown['total_rewards']
                annual_fee = float(card.annual_fee)
                net_value = annual_rewards - annual_fee

                if net_value >= 0 or annual_fee == 0:
                    actions.append({
                        'card': card,
                        'action': 'keep',
                        'reasoning': f"Keep - earning ${annual_rewards:.0f} annually vs ${annual_fee} fee",
                        'priority': 2
                    })
                else:
                    actions.append({
                        'card': card,
                        'action': 'cancel',
                        'reasoning': f"Cancel - provides no additional portfolio value (${annual_rewards:.0f} rewards vs ${annual_fee} fee)",
                        'priority': 1
                    })

            remaining_slots = max_total_cards - len(cards_to_keep)
            if remaining_slots > 0 and available_cards:
                if len(cards_to_keep) == 0:
                    logger.debug(f"Scenario 1 using portfolio optimization for {len(available_cards)} available cards")
                    return self.select_optimal_card_combination(available_cards, max_total_cards)
                else:
                    logger.debug(f"Scenario 2 using FULL portfolio optimization with {len(cards_to_keep)} current + {len(available_cards)} new cards")
                    all_cards = list(cards_to_keep) + available_cards
                    full_optimization = self.select_optimal_card_combination(all_cards, max_total_cards)

                    best_new_cards = self.select_best_new_cards(available_cards, remaining_slots)
                    actions.extend(best_new_cards)
                    keep_all_value = self.calculate_scenario_portfolio_value(actions)

                    if full_optimization and full_optimization['net_portfolio_value'] > keep_all_value:
                        logger.debug(f"Full optimization better: ${full_optimization['net_portfolio_value']:.2f} vs ${keep_all_value:.2f}")
                        return full_optimization
                    else:
                        logger.debug(f"Keep-all scenario better: ${keep_all_value:.2f} vs ${full_optimization.get('net_portfolio_value', 0):.2f}")

            portfolio_value = self.calculate_scenario_portfolio_value(actions)
            return {
                'actions': actions,
                'net_portfolio_value': portfolio_value
            }

    def select_optimal_card_combination(self, all_cards: List[CreditCard], max_cards: int) -> dict:
        """Select optimal combination of cards from all available."""
        current_card_ids = {uc.card.id for uc in self.engine.user_cards}
        card_scores = []
        for card in all_cards:
            if card.id in current_card_ids:
                annual_rewards = self.calculate_smart_card_value(card, signup_bonus=False)
                annual_fee = float(card.annual_fee)
                base_net_value = annual_rewards - annual_fee
                action = 'keep'
                signup_bonus_value = 0
            else:
                if not self.engine._is_eligible_for_card(card):
                    continue
                annual_rewards = self.calculate_smart_card_value(card, signup_bonus=False)
                signup_bonus_value = self.engine._get_signup_bonus_value(card)

                if self.engine._bonus_months_needed(card) > self.engine.BONUS_CAPACITY_MONTHS:
                    signup_bonus_value = 0
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else float(card.annual_fee)
                base_net_value = annual_rewards - effective_fee + signup_bonus_value
                action = 'apply'

            scored_value = (base_net_value
                            + signup_bonus_value * (self.engine.weights['signup_bonus_weight'] - 1)
                            - self.engine.weights['per_card_penalty'])

            efficiency_score = self.calculate_spending_efficiency(card)
            if efficiency_score > 0.8:
                efficiency_boost = scored_value * efficiency_score * 2.0
            else:
                efficiency_boost = scored_value * efficiency_score * 1.0
            net_value = scored_value + efficiency_boost

            card_scores.append({
                'card': card,
                'action': action,
                'net_value': net_value,
                'base_net_value': base_net_value,
                'efficiency_score': efficiency_score,
                'efficiency_boost': efficiency_boost,
                'annual_rewards': annual_rewards,
                'signup_bonus': signup_bonus_value,
                'current_card': card.id in current_card_ids
            })

        optimal_cards = self.optimize_card_portfolio(card_scores, max_cards)

        actions = []
        for i, card_data in enumerate(optimal_cards):
            reasoning = self.generate_card_reasoning(card_data)
            actions.append({
                'card': card_data['card'],
                'action': card_data['action'],
                'reasoning': reasoning,
                'priority': i + 1
            })

        optimal_card_ids = {cd['card'].id for cd in optimal_cards}
        held_for_optimal = [cd['card'] for cd in optimal_cards]
        portfolio_allocation = self.engine._calculate_portfolio_allocation(held_for_optimal)
        credit_allocation = self.engine._allocate_portfolio_credits(held_for_optimal)
        program_multipliers = self.engine._program_multipliers(held_for_optimal)

        for uc in self.engine.user_cards:
            if uc.card.id not in optimal_card_ids:
                annual_fee = float(uc.card.annual_fee)
                rewards_breakdown = self.engine._calculate_card_allocated_breakdown(
                    uc.card, portfolio_allocation, credit_allocation, program_multipliers)
                annual_rewards = rewards_breakdown['total_rewards']

                if annual_fee == 0:
                    logger.debug(f"Keeping $0 fee card instead of canceling: {uc.card.name}")
                    actions.append({
                        'card': uc.card,
                        'action': 'keep',
                        'reasoning': f"Keep - no annual fee card (${annual_rewards:.0f} rewards, $0 fee)",
                        'priority': 60
                    })
                else:
                    logger.debug(f"Recommending cancel for fee card: {uc.card.name} (${annual_fee} fee)")
                    actions.append({
                        'card': uc.card,
                        'action': 'cancel',
                        'reasoning': f"Cancel - provides no additional portfolio value (${annual_rewards:.0f} rewards vs ${annual_fee:.0f} fee)",
                        'priority': 50
                    })

        portfolio_value = self.calculate_scenario_portfolio_value(actions)
        return {
            'actions': actions,
            'net_portfolio_value': portfolio_value
        }

    def optimize_card_portfolio(self, card_scores: List[dict], max_cards: int) -> List[dict]:
        """Use portfolio optimization to select best card combination avoiding double counting."""
        spending_by_category = {}
        for category_slug, monthly_amount in self.engine.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            if annual_spend > 0:
                spending_by_category[category_slug] = annual_spend

        def calculate_portfolio_value(card_combination):
            total_value = 0
            total_fees = 0
            category_allocated = {}

            apply_cards_in_combination = [cd['card'] for cd in card_combination
                                          if cd['action'] == 'apply']
            held_cards_in_combination = [cd['card'] for cd in card_combination
                                         if cd['action'] in ('keep', 'apply')]
            combination_program_multipliers = self.engine._program_multipliers(held_cards_in_combination)
            combination_capacity_plan = self.engine._bonus_capacity_plan(
                apply_cards_in_combination, combination_program_multipliers)

            for card_data in card_combination:
                card = card_data['card']
                if card_data['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                    pass
                else:
                    total_fees += float(card.annual_fee)

                if card_data['action'] == 'apply':
                    entry = combination_capacity_plan['by_card_id'].get(card.id)
                    if entry and entry['counted']:
                        total_value += entry['bonus_value'] * self.engine.weights['signup_bonus_weight']

                for reward_cat in card.reward_categories.active_on(self.engine.today):
                    category_slug = reward_cat.category.slug
                    rate = float(reward_cat.reward_rate)
                    max_spend = reward_cat.max_annual_spend

                    if category_slug not in category_allocated or rate > category_allocated[category_slug]['rate']:
                        category_allocated[category_slug] = {
                            'rate': rate,
                            'max_spend': max_spend,
                            'card': card,
                            'multiplier': self.engine._effective_multiplier(card, combination_program_multipliers)
                        }

            for category_slug, annual_spend in spending_by_category.items():
                if category_slug in category_allocated:
                    allocation = category_allocated[category_slug]
                    rate = allocation['rate']
                    max_spend = allocation['max_spend']
                    multiplier = allocation['multiplier']

                    effective_spend = annual_spend
                    if max_spend:
                        effective_spend = min(annual_spend, float(max_spend))

                    category_rewards = effective_spend * rate * float(multiplier)
                    total_value += category_rewards

            credit_allocation = self.engine._allocate_portfolio_credits(
                [cd['card'] for cd in card_combination])
            total_value += sum(value for value, _ in credit_allocation.values())

            card_count_cost = self.engine.weights['per_card_penalty'] * len(card_combination)
            return total_value - total_fees - card_count_cost

        best_combination = []
        best_value = 0

        must_include = [cd for cd in card_scores if cd['action'] == 'keep']
        remaining_cards = [cd for cd in card_scores if cd not in must_include]

        logger.debug(f"Portfolio optimization - must_include: {len(must_include)}, remaining: {len(remaining_cards)}, max_cards: {max_cards}")

        empty_portfolio_value = calculate_portfolio_value([])
        if empty_portfolio_value > best_value:
            best_value = empty_portfolio_value
            best_combination = []

        remaining_cards.sort(key=lambda x: x['net_value'], reverse=True)
        cards_to_test = remaining_cards[:min(20, len(remaining_cards))]

        current_combination = must_include.copy()
        current_value = calculate_portfolio_value(current_combination) if current_combination else 0

        if current_value > best_value:
            best_value = current_value
            best_combination = current_combination.copy()

        available_cards = cards_to_test.copy()

        while len(current_combination) < max_cards and available_cards:
            best_addition = None
            best_addition_value = current_value

            for card_to_add in available_cards:
                test_combination = current_combination + [card_to_add]
                test_actions = [{'card': cd['card'], 'action': cd['action']} for cd in test_combination]
                test_value = self.calculate_scenario_portfolio_value(test_actions)

                if test_value > best_addition_value:
                    best_addition_value = test_value
                    best_addition = card_to_add

            if best_addition and best_addition_value > current_value:
                current_combination.append(best_addition)
                available_cards.remove(best_addition)
                current_value = best_addition_value

                if current_value > best_value:
                    best_value = current_value
                    best_combination = current_combination.copy()
            else:
                break

        if best_value <= 0:
            return []

        return best_combination[:max_cards]

    def generate_card_reasoning(self, card_data: dict) -> str:
        """Generate reasoning text for a card recommendation."""
        card = card_data['card']
        action = card_data['action']

        if action == 'apply':
            rewards_breakdown = self.engine._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus = self.engine._get_signup_bonus_value(card)
            annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
            effective_fee = 0 if annual_fee_waived else float(card.annual_fee)
            total_estimated_value = annual_rewards - effective_fee + signup_bonus

            if signup_bonus > 0:
                return f"Total estimated value: ${total_estimated_value:.0f} (${annual_rewards:.0f} annual rewards - ${effective_fee} fee + ${signup_bonus:.0f} signup bonus)"
            else:
                return f"Total estimated value: ${total_estimated_value:.0f} (${annual_rewards:.0f} annual rewards - ${effective_fee} fee)"
        elif action == 'keep':
            rewards_breakdown = self.engine._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            net_value = annual_rewards - annual_fee
            return f"Keep - earning ${annual_rewards:.0f} annually vs ${annual_fee} fee (net: ${net_value:.0f})"
        else:
            return f"Cancel - redundant card providing negative portfolio value"

    def select_best_new_cards(self, available_cards: List[CreditCard], max_new_cards: int) -> List[dict]:
        """Select best new cards to apply for."""
        actions = []
        card_scores = []

        for card in available_cards:
            if not self.engine._is_eligible_for_card(card):
                continue

            rewards_breakdown = self.engine._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus_value = self.engine._get_signup_bonus_value(card)
            annual_fee = float(card.annual_fee)
            annual_fee_waived_first_year = card.metadata.get('annual_fee_waived_first_year', False)
            effective_annual_fee = 0 if annual_fee_waived_first_year else annual_fee

            net_annual_value = annual_rewards - effective_annual_fee
            total_value = net_annual_value + signup_bonus_value

            if total_value > 0:
                card_scores.append({
                    'card': card,
                    'total_value': total_value,
                    'net_annual_value': net_annual_value,
                    'signup_bonus': signup_bonus_value,
                    'rewards_breakdown': rewards_breakdown['breakdown'],
                    'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0)
                })

        card_scores.sort(key=lambda x: x['total_value'], reverse=True)

        for i, card_data in enumerate(card_scores[:max_new_cards]):
            reasoning = f"Apply - ${card_data['total_value']:.0f} total value (${card_data['net_annual_value']:.0f} annual + ${card_data['signup_bonus']:.0f} signup bonus)"
            actions.append({
                'card': card_data['card'],
                'action': 'apply',
                'reasoning': reasoning,
                'priority': i + 10
            })

        return actions

    def calculate_scenario_portfolio_value(self, actions: List[dict]) -> float:
        """Calculate net portfolio value for a scenario using fast portfolio optimization."""
        portfolio_cards = [action for action in actions if action['action'] in ['keep', 'apply']]

        if not portfolio_cards:
            return 0.0

        total_annual_fees = 0
        total_signup_bonuses = 0

        apply_cards_in_scenario = [action['card'] for action in portfolio_cards
                                   if action['action'] == 'apply']
        held_cards_in_scenario = [action['card'] for action in portfolio_cards]
        scenario_program_multipliers = self.engine._program_multipliers(held_cards_in_scenario)
        capacity_plan = self.engine._bonus_capacity_plan(
            apply_cards_in_scenario, scenario_program_multipliers)

        for action in portfolio_cards:
            card = action['card']
            if action['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                total_annual_fees += 0
            else:
                total_annual_fees += float(card.annual_fee)

            if action['action'] == 'apply':
                entry = capacity_plan['by_card_id'].get(card.id)
                if entry and entry['counted']:
                    total_signup_bonuses += (entry['bonus_value']
                                             * self.engine.weights['signup_bonus_weight'])

        credit_allocation = self.engine._allocate_portfolio_credits(
            [action['card'] for action in portfolio_cards])
        total_credits_value = sum(value for value, _ in credit_allocation.values())

        if not hasattr(self.engine, '_cached_parent_spending'):
            self.engine._cached_parent_spending = self.engine._build_parent_category_spending()

        parent_category_spending = self.engine._cached_parent_spending

        category_best_rates = {}

        for action in portfolio_cards:
            card = action['card']
            if not hasattr(card, '_cached_reward_categories'):
                card._cached_reward_categories = list(card.reward_categories.active_on(self.engine.today).select_related('category'))

            for reward_category in card._cached_reward_categories:
                category_slug = reward_category.category.slug
                reward_rate = float(reward_category.reward_rate)

                if parent_category_spending.get(category_slug, 0) > 0:
                    if category_slug not in category_best_rates or reward_rate > category_best_rates[category_slug]['rate']:
                        category_best_rates[category_slug] = {
                            'rate': reward_rate,
                            'card': card,
                            'max_spend': reward_category.max_annual_spend
                        }

        total_portfolio_rewards = 0
        allocated_spending = 0

        for category_slug, rate_data in category_best_rates.items():
            annual_spend = parent_category_spending.get(category_slug, 0.0)

            if annual_spend > 0:
                if rate_data['max_spend']:
                    annual_spend = min(annual_spend, float(rate_data['max_spend']))

                allocated_spending += annual_spend
                reward_rate = rate_data['rate']
                best_card = rate_data['card']

                reward_value_multiplier = self.engine._effective_multiplier(
                    best_card, scenario_program_multipliers)
                points_earned = annual_spend * reward_rate
                category_rewards = points_earned * reward_value_multiplier
                total_portfolio_rewards += category_rewards

        total_parent_spending = sum(parent_category_spending.values())
        unallocated_spending = total_parent_spending - allocated_spending

        if unallocated_spending > 0:
            best_general_rate = 1.0
            best_general_multiplier = 0.01

            for action in portfolio_cards:
                card = action['card']
                for reward_category in card._cached_reward_categories:
                    if reward_category.category.slug in ['general', 'other', 'everything-else']:
                        rate = float(reward_category.reward_rate)
                        if rate > best_general_rate:
                            best_general_rate = rate
                            best_general_multiplier = self.engine._effective_multiplier(
                                card, scenario_program_multipliers)

            general_rewards = unallocated_spending * best_general_rate * float(best_general_multiplier)
            total_portfolio_rewards += general_rewards

        base_portfolio_value = (total_portfolio_rewards + total_credits_value
                                + total_signup_bonuses - total_annual_fees)

        total_efficiency_boost = 0
        for action in portfolio_cards:
            card = action['card']
            efficiency_score = self.calculate_spending_efficiency(card)

            if efficiency_score > 0.1:
                card_annual_value = self.calculate_smart_card_value(card, signup_bonus=False) - float(card.annual_fee)
                if action['action'] == 'apply':
                    entry = capacity_plan['by_card_id'].get(card.id)
                    card_signup_value = ((entry['bonus_value'] * self.engine.weights['signup_bonus_weight'])
                                         if entry and entry['counted'] else 0)
                else:
                    card_signup_value = 0
                card_base_value = card_annual_value + card_signup_value
                efficiency_boost = card_base_value * efficiency_score * 0.5
                total_efficiency_boost += efficiency_boost

        card_count_cost = self.engine.weights['per_card_penalty'] * len(portfolio_cards)
        final_value = base_portfolio_value + total_efficiency_boost - card_count_cost

        return final_value

    def calculate_smart_card_value(self, card: CreditCard, signup_bonus: bool = True) -> float:
        """Calculate card value considering actual user spending and category competition."""
        if not hasattr(self.engine, '_cached_parent_spending'):
            self.engine._cached_parent_spending = self.engine._build_parent_category_spending()

        parent_category_spending = self.engine._cached_parent_spending
        total_rewards = 0

        if not hasattr(card, '_cached_reward_categories'):
            card._cached_reward_categories = list(card.reward_categories.active_on(self.engine.today).select_related('category'))

        for reward_category in card._cached_reward_categories:
            category_slug = reward_category.category.slug
            annual_spend = parent_category_spending.get(category_slug, 0.0)

            if annual_spend == 0:
                for orig_category_slug, monthly_amount in self.engine.spending_amounts.items():
                    if orig_category_slug == category_slug:
                        annual_spend = float(monthly_amount) * 12
                        break

            if annual_spend > 0:
                reward_rate = float(reward_category.reward_rate)
                effective_spend = annual_spend
                if reward_category.max_annual_spend:
                    effective_spend = min(annual_spend, float(reward_category.max_annual_spend))

                reward_value_multiplier = self.engine._own_multiplier(card)
                category_rewards = effective_spend * reward_rate * reward_value_multiplier
                total_rewards += category_rewards

        # Add single-card credits value
        credits_value, _ = self.engine._calculate_card_credits_value(card)
        total_rewards += credits_value

        if signup_bonus:
            signup_value = self.engine._get_signup_bonus_value(card)
            total_rewards += signup_value

        return total_rewards

    def calculate_spending_efficiency(self, card: CreditCard) -> float:
        """Calculate how efficiently a card matches user's actual spending pattern."""
        if not hasattr(self.engine, '_cached_parent_spending'):
            self.engine._cached_parent_spending = self.engine._build_parent_category_spending()

        parent_category_spending = self.engine._cached_parent_spending
        total_user_spending = sum(parent_category_spending.values())

        if total_user_spending == 0:
            return 0.0

        if not hasattr(card, '_cached_reward_categories'):
            card._cached_reward_categories = list(card.reward_categories.active_on(self.engine.today).select_related('category'))

        relevant_spending = 0.0
        weighted_efficiency = 0.0

        for reward_category in card._cached_reward_categories:
            category_slug = reward_category.category.slug
            annual_spend = parent_category_spending.get(category_slug, 0.0)

            if annual_spend == 0:
                for orig_category_slug, monthly_amount in self.engine.spending_amounts.items():
                    if orig_category_slug == category_slug:
                        annual_spend = float(monthly_amount) * 12
                        break

            if annual_spend > 0:
                reward_rate = float(reward_category.reward_rate)
                spending_weight = annual_spend / total_user_spending
                efficiency = max(0, (reward_rate - 1.0) / 4.0)
                efficiency = min(1.0, efficiency)

                weighted_efficiency += efficiency * spending_weight
                relevant_spending += annual_spend

        coverage_ratio = relevant_spending / total_user_spending
        final_score = (weighted_efficiency * 0.7) + (coverage_ratio * 0.3)
        return min(1.0, final_score)

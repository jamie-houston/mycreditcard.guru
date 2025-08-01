from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from cards.models import CreditCard, UserSpendingProfile, UserCard
from .models import Roadmap


class RecommendationEngine:
    """
    Core recommendation engine that considers:
    - User spending patterns
    - Issuer policies (5/24 rule, etc.)
    - Reward optimization
    - Annual fee vs. benefits analysis
    """
    
    def __init__(self, profile: UserSpendingProfile):
        self.profile = profile
        self.user_cards = list(profile.user_cards.filter(is_active=True))
        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount 
            for sa in profile.spending_amounts.all()
        }
        
    
    def generate_quick_recommendations(self, roadmap: Roadmap) -> List[dict]:
        """Generate recommendations without saving to database (includes breakdowns)"""
        # Reload spending amounts to ensure we have the latest data
        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount 
            for sa in self.profile.spending_amounts.all()
        }
        print(f"DEBUG: Reloaded spending_amounts: {dict(self.spending_amounts)}")
        
        # Get all eligible cards based on filters
        eligible_cards = self._get_filtered_cards(roadmap)
        
        # Generate portfolio-optimized recommendations
        recommendations = self._generate_portfolio_optimized_recommendations(eligible_cards, roadmap)
        
        # DEBUG: Print recommendations before filtering
        print(f"DEBUG: Generated {len(recommendations)} recommendations before filtering:")
        for rec in recommendations:
            print(f"  - {rec['action'].upper()}: {rec['card'].name} (priority: {rec['priority']})")
        
        # Separate recommendations by action type for smart filtering
        keeps_and_applies = [rec for rec in recommendations if rec['action'] in ['keep', 'apply', 'upgrade', 'downgrade']]
        cancels = [rec for rec in recommendations if rec['action'] == 'cancel']
        
        # Separate $0 fee keeps (always show) from other keeps/applies
        zero_fee_keeps = [rec for rec in keeps_and_applies if rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0]
        other_keeps_applies = [rec for rec in keeps_and_applies if not (rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0)]
        
        # Sort other keeps/applies by priority (lower number = higher priority)
        other_keeps_applies.sort(key=lambda x: x['priority'])
        
        # Always include $0 fee keeps and cancels, limit other keeps/applies
        max_other_keeps_applies = roadmap.max_recommendations
        
        # Reserve space for zero fee keeps and cancels
        reserved_slots = len(zero_fee_keeps)
        if cancels:
            # Reserve at least 1-2 slots for cancels, but don't go below 2 other keeps/applies
            cancel_slots = min(len(cancels), max(1, roadmap.max_recommendations // 3))
            reserved_slots += cancel_slots
        
        max_other_keeps_applies = max(1, roadmap.max_recommendations - reserved_slots)
        
        # Take top other keeps/applies, all zero fee keeps, and all cancels
        filtered_other_keeps_applies = other_keeps_applies[:max_other_keeps_applies]
        recommendations = filtered_other_keeps_applies + zero_fee_keeps + cancels
        
        # DEBUG: Print smart filtering details
        print(f"DEBUG: Smart filtering breakdown:")
        print(f"  - Other keeps/applies: {len(filtered_other_keeps_applies)}")
        print(f"  - Zero fee keeps: {len(zero_fee_keeps)}")
        print(f"  - Cancels: {len(cancels)}")
        print(f"DEBUG: Final {len(recommendations)} recommendations after smart filtering:")
        for rec in recommendations:
            fee_info = f" (${rec['card'].annual_fee} fee)" if rec['action'] == 'keep' else ""
            print(f"  - {rec['action'].upper()}: {rec['card'].name}{fee_info} (priority: {rec['priority']})")
        
        # Calculate portfolio summary for the recommended cards
        portfolio_summary = self._calculate_portfolio_summary(recommendations)
        
        # Filter rewards breakdown to only show for top-performing cards per category
        optimal_cards = portfolio_summary.get('category_optimization_cards', set())
        for rec in recommendations:
            # Only keep rewards breakdown for cards that are optimal for at least one category
            if rec['card'].name not in optimal_cards:
                # Keep only the credits breakdown, remove spending-based rewards
                filtered_breakdown = []
                for breakdown_item in rec.get('rewards_breakdown', []):
                    # Keep Card Benefits & Credits breakdown, filter out spending categories
                    if 'Card Benefits' in breakdown_item.get('category_name', ''):
                        filtered_breakdown.append(breakdown_item)
                rec['rewards_breakdown'] = filtered_breakdown
            
            # Add portfolio summary to each recommendation for frontend access
            rec['portfolio_summary'] = portfolio_summary
        
        return recommendations
    
    def generate_roadmap(self, roadmap: 'Roadmap') -> List[dict]:
        """Generate recommendations and save them to the database"""
        from .models import RoadmapRecommendation, RoadmapCalculation
        
        # Clear existing recommendations for this roadmap
        roadmap.recommendations.all().delete()
        
        # Generate new recommendations using the same logic as quick recommendations
        recommendations = self.generate_quick_recommendations(roadmap)
        
        # Save recommendations to database
        saved_recommendations = []
        for rec in recommendations:
            recommendation = RoadmapRecommendation.objects.create(
                roadmap=roadmap,
                card=rec['card'],
                action=rec['action'],
                priority=rec['priority'],
                estimated_rewards=rec['estimated_rewards'],
                reasoning=rec['reasoning']
            )
            saved_recommendations.append(recommendation)
        
        # Calculate and save total estimated rewards
        total_rewards = self._calculate_total_rewards(recommendations)
        calculation, _ = RoadmapCalculation.objects.update_or_create(
            roadmap=roadmap,
            defaults={
                'total_estimated_rewards': total_rewards,
                'calculation_data': {
                    'breakdown': [
                        {
                            'card_name': rec['card'].name,
                            'action': rec['action'],
                            'estimated_rewards': float(rec['estimated_rewards']),
                            'reasoning': rec['reasoning'],
                            'rewards_breakdown': rec.get('rewards_breakdown', [])
                        }
                        for rec in recommendations
                    ],
                    'total_rewards': float(total_rewards)
                }
            }
        )
        
        return recommendations
    
    def _get_filtered_cards(self, roadmap: Roadmap) -> List[CreditCard]:
        """Apply roadmap filters to get eligible cards"""
        queryset = CreditCard.objects.filter(is_active=True)
        
        for filter_obj in roadmap.filters.all():
            if filter_obj.filter_type == 'issuer':
                queryset = queryset.filter(issuer__name__icontains=filter_obj.value)
            elif filter_obj.filter_type == 'reward_type':
                queryset = queryset.filter(primary_reward_type__name__icontains=filter_obj.value)
            elif filter_obj.filter_type == 'card_type':
                queryset = queryset.filter(card_type=filter_obj.value)
            elif filter_obj.filter_type == 'annual_fee':
                # Expect format like "0" or "0-95" or "95+"
                from decimal import Decimal
                if '+' in filter_obj.value:
                    min_fee = Decimal(filter_obj.value.replace('+', ''))
                    queryset = queryset.filter(annual_fee__gte=min_fee)
                elif '-' in filter_obj.value:
                    min_fee, max_fee = map(Decimal, filter_obj.value.split('-'))
                    queryset = queryset.filter(annual_fee__gte=min_fee, annual_fee__lte=max_fee)
                else:
                    fee = Decimal(filter_obj.value)
                    queryset = queryset.filter(annual_fee=fee)
        
        # Filter out discontinued cards
        all_cards = list(queryset.prefetch_related('reward_categories', 'credits'))
        active_cards = [card for card in all_cards if not card.metadata.get('discontinued', False)]
        
        return active_cards
    
    def _generate_portfolio_optimized_recommendations(self, eligible_cards: List[CreditCard], roadmap: Roadmap) -> List[dict]:
        """Generate portfolio-optimized recommendations considering all cards together"""
        recommendations = []
        
        # Create a combined pool of current + potential cards
        current_cards = [uc.card for uc in self.user_cards]
        available_new_cards = [c for c in eligible_cards if c.id not in {card.id for card in current_cards}]
        
        # DEBUG: Print current cards
        print(f"DEBUG: User has {len(current_cards)} current cards:")
        for card in current_cards:
            print(f"  - {card.name}")
        print(f"DEBUG: Found {len(available_new_cards)} available new cards")
        print(f"DEBUG: Max recommendations allowed: {roadmap.max_recommendations}")
        print(f"DEBUG: Will scenario 1 use optimization? {len(current_cards) == 0}")
        print(f"DEBUG: Will scenario 2 use optimization? {True}")
        
        # Generate all possible portfolio combinations and evaluate them
        best_portfolio = self._find_optimal_portfolio(current_cards, available_new_cards, roadmap.max_recommendations)
        
        # Convert optimal portfolio to recommendations
        for card_action in best_portfolio:
            card = card_action['card']
            action = card_action['action']
            
            # Calculate individual card breakdown for display
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            
            # For individual card display, calculate net value
            if action == 'apply':
                signup_bonus_value = self._get_signup_bonus_value(card)
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else annual_fee
                estimated_value = annual_rewards - effective_fee + signup_bonus_value
                reasoning = card_action.get('reasoning', f"Apply - adds ${estimated_value:.0f} value to portfolio")
            else:  # keep or cancel
                estimated_value = annual_rewards - annual_fee
                reasoning = card_action.get('reasoning', f"{action.title()} - portfolio optimization decision")
            
            recommendations.append({
                'card': card,
                'action': action,
                'estimated_rewards': Decimal(str(max(0, estimated_value))),  # Don't show negative individual values
                'reasoning': reasoning,
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'priority': card_action.get('priority', 1)
            })
        
        return recommendations
    
    def _find_optimal_portfolio(self, current_cards: List[CreditCard], available_cards: List[CreditCard], max_cards: int) -> List[dict]:
        """Find the optimal combination of cards for maximum portfolio value"""
        # Start with current cards and evaluate what to do with each
        portfolio_actions = []
        
        # Evaluate portfolio scenarios
        scenarios = []
        
        # Scenario 1: Keep all current cards, add best new cards
        scenario1 = self._evaluate_portfolio_scenario(
            cards_to_keep=current_cards,
            cards_to_apply=[],
            available_cards=available_cards,
            max_total_cards=max_cards
        )
        scenarios.append(("keep_all_add_new", scenario1))
        
        # Scenario 2: Optimize current cards (may cancel some), add best new cards
        scenario2 = self._evaluate_portfolio_scenario(
            cards_to_keep=[],  # Will evaluate each current card
            cards_to_apply=current_cards + available_cards,  # All cards considered equally
            available_cards=[],
            max_total_cards=max_cards
        )
        scenarios.append(("full_optimization", scenario2))
        
        # DEBUG: Print scenario comparison
        print(f"DEBUG: Scenario comparison:")
        for name, scenario in scenarios:
            actions_summary = {}
            for action in scenario['actions']:
                action_type = action['action']
                actions_summary[action_type] = actions_summary.get(action_type, 0) + 1
            print(f"  {name}: value=${scenario['net_portfolio_value']:.2f}, actions={actions_summary}")
        
        # Choose best scenario
        best_scenario = max(scenarios, key=lambda x: x[1]['net_portfolio_value'])
        print(f"DEBUG: Selected scenario: {best_scenario[0]} with value ${best_scenario[1]['net_portfolio_value']:.2f}")
        return best_scenario[1]['actions']
    
    def _evaluate_portfolio_scenario(self, cards_to_keep: List[CreditCard], cards_to_apply: List[CreditCard], 
                                   available_cards: List[CreditCard], max_total_cards: int) -> dict:
        """Evaluate a specific portfolio scenario and return optimized actions"""
        
        if not cards_to_keep and cards_to_apply:
            # Full optimization mode - select best cards from all available
            return self._select_optimal_card_combination(cards_to_apply, max_total_cards)
        else:
            # Keep specified cards, add best available
            actions = []
            
            # Add keep actions for specified cards, but cancel if they lose money
            for card in cards_to_keep:
                rewards_breakdown = self._calculate_card_rewards_breakdown(card)
                annual_rewards = rewards_breakdown['total_rewards']
                annual_fee = float(card.annual_fee)
                net_value = annual_rewards - annual_fee
                
                # Only keep cards that provide positive value, or zero-fee cards
                if net_value >= 0 or annual_fee == 0:
                    actions.append({
                        'card': card,
                        'action': 'keep',
                        'reasoning': f"Keep - earning ${annual_rewards:.0f} annually vs ${annual_fee} fee",
                        'priority': 2
                    })
                else:
                    # Cancel money-losing cards
                    actions.append({
                        'card': card,
                        'action': 'cancel',
                        'reasoning': f"Cancel - provides no additional portfolio value (${annual_rewards:.0f} rewards vs ${annual_fee} fee)",
                        'priority': 1
                    })
            
            # Add best available cards up to limit
            remaining_slots = max_total_cards - len(cards_to_keep)
            if remaining_slots > 0 and available_cards:
                # If no cards to keep, use full portfolio optimization
                if len(cards_to_keep) == 0:
                    print(f"DEBUG: Scenario 1 using portfolio optimization for {len(available_cards)} available cards")
                    return self._select_optimal_card_combination(available_cards, max_total_cards)
                else:
                    # ALWAYS use full optimization to consider dropping current cards for better new ones
                    print(f"DEBUG: Scenario 2 using FULL portfolio optimization with {len(cards_to_keep)} current + {len(available_cards)} new cards")
                    all_cards = list(cards_to_keep) + available_cards
                    full_optimization = self._select_optimal_card_combination(all_cards, max_total_cards)
                    
                    # Compare with keep-all scenario
                    best_new_cards = self._select_best_new_cards(available_cards, remaining_slots)
                    actions.extend(best_new_cards)
                    keep_all_value = self._calculate_scenario_portfolio_value(actions)
                    
                    # Use full optimization if it's better
                    if full_optimization and full_optimization['net_portfolio_value'] > keep_all_value:
                        print(f"DEBUG: Full optimization better: ${full_optimization['net_portfolio_value']:.2f} vs ${keep_all_value:.2f}")
                        return full_optimization
                    else:
                        print(f"DEBUG: Keep-all scenario better: ${keep_all_value:.2f} vs ${full_optimization.get('net_portfolio_value', 0):.2f}")
                        # Keep the current logic (actions already extended above)
            
            # Calculate portfolio value
            portfolio_value = self._calculate_scenario_portfolio_value(actions)
            
            return {
                'actions': actions,
                'net_portfolio_value': portfolio_value
            }
    
    def _select_optimal_card_combination(self, all_cards: List[CreditCard], max_cards: int) -> dict:
        """Select optimal combination of cards from all available (current + new)"""
        current_card_ids = {uc.card.id for uc in self.user_cards}
        
        # Score all cards using smart portfolio-aware calculation with efficiency scoring
        card_scores = []
        for card in all_cards:
            if card.id in current_card_ids:
                # Current card - no signup bonus
                annual_rewards = self._calculate_smart_card_value(card, signup_bonus=False)
                annual_fee = float(card.annual_fee)
                base_net_value = annual_rewards - annual_fee
                action = 'keep'
                signup_bonus_value = 0
            else:
                # New card - include signup bonus
                if not self._is_eligible_for_card(card):
                    continue
                annual_rewards = self._calculate_smart_card_value(card, signup_bonus=False)
                signup_bonus_value = self._get_signup_bonus_value(card)
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else float(card.annual_fee)
                base_net_value = annual_rewards - effective_fee + signup_bonus_value
                action = 'apply'
            
            # Apply efficiency scoring: boost cards that are highly relevant to user's spending
            efficiency_score = self._calculate_spending_efficiency(card)
            if efficiency_score > 0.8:  # Super boost for highly relevant cards
                efficiency_boost = base_net_value * efficiency_score * 2.0  # Up to 200% boost for perfect efficiency
            else:
                efficiency_boost = base_net_value * efficiency_score * 1.0  # Up to 100% boost for normal cards
            net_value = base_net_value + efficiency_boost
            
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
        
        # Use portfolio optimization to select best combination
        optimal_cards = self._optimize_card_portfolio(card_scores, max_cards)
        
        # Convert to actions
        actions = []
        for i, card_data in enumerate(optimal_cards):
            reasoning = self._generate_card_reasoning(card_data)
            actions.append({
                'card': card_data['card'],
                'action': card_data['action'],
                'reasoning': reasoning,
                'priority': i + 1
            })
        
        # Add cancel actions for current cards not in optimal portfolio
        # BUT: Never recommend canceling cards with $0 annual fee
        optimal_card_ids = {cd['card'].id for cd in optimal_cards}
        for uc in self.user_cards:
            if uc.card.id not in optimal_card_ids:
                annual_fee = float(uc.card.annual_fee)
                
                # Skip cancellation recommendations for $0 annual fee cards
                if annual_fee == 0:
                    # Instead, add as a "keep" recommendation with low priority
                    rewards_breakdown = self._calculate_card_rewards_breakdown(uc.card)
                    annual_rewards = rewards_breakdown['total_rewards']
                    print(f"DEBUG: Keeping $0 fee card instead of canceling: {uc.card.name}")
                    actions.append({
                        'card': uc.card,
                        'action': 'keep',
                        'reasoning': f"Keep - no annual fee card (${annual_rewards:.0f} rewards, $0 fee)",
                        'priority': 60  # Lower priority than optimal keeps
                    })
                else:
                    # Only recommend canceling cards with annual fees
                    rewards_breakdown = self._calculate_card_rewards_breakdown(uc.card)
                    annual_rewards = rewards_breakdown['total_rewards']
                    print(f"DEBUG: Recommending cancel for fee card: {uc.card.name} (${annual_fee} fee)")
                    actions.append({
                        'card': uc.card,
                        'action': 'cancel',
                        'reasoning': f"Cancel - provides no additional portfolio value (${annual_rewards:.0f} rewards vs ${annual_fee} fee)",
                        'priority': 50  # Medium priority - important to show user
                    })
        
        portfolio_value = self._calculate_scenario_portfolio_value(actions)
        
        return {
            'actions': actions,
            'net_portfolio_value': portfolio_value
        }
    
    def _optimize_card_portfolio(self, card_scores: List[dict], max_cards: int) -> List[dict]:
        """Use portfolio optimization to select best card combination avoiding double counting"""
        from collections import defaultdict
        from itertools import combinations
        
        # Build category coverage map
        category_coverage = defaultdict(list)
        
        for card_data in card_scores:
            card = card_data['card']
            for reward_cat in card.reward_categories.filter(is_active=True):
                category_slug = reward_cat.category.slug
                category_coverage[category_slug].append({
                    'card_data': card_data,
                    'rate': float(reward_cat.reward_rate),
                    'max_spend': reward_cat.max_annual_spend
                })
        
        # Get user spending by category
        spending_by_category = {}
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            if annual_spend > 0:
                spending_by_category[category_slug] = annual_spend
        
        # Function to calculate true portfolio value for a set of cards
        def calculate_portfolio_value(card_combination):
            total_value = 0
            total_fees = 0
            category_allocated = {}  # Track best rate per category
            
            # Calculate credits/benefits value for each card
            for card_data in card_combination:
                card = card_data['card']
                
                # Add annual fee
                if card_data['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                    # First year fee waived
                    pass
                else:
                    total_fees += float(card.annual_fee)
                
                # Add signup bonus for new cards
                if card_data['action'] == 'apply':
                    signup_bonus = self._get_signup_bonus_value(card)
                    total_value += signup_bonus
                
                # Add credits/benefits value
                credits_value, _ = self._calculate_card_credits_value(card)
                total_value += credits_value
                
                # Track best reward rate per category across all cards
                for reward_cat in card.reward_categories.filter(is_active=True):
                    category_slug = reward_cat.category.slug
                    rate = float(reward_cat.reward_rate)
                    max_spend = reward_cat.max_annual_spend
                    
                    if category_slug not in category_allocated or rate > category_allocated[category_slug]['rate']:
                        category_allocated[category_slug] = {
                            'rate': rate,
                            'max_spend': max_spend,
                            'card': card,
                            'multiplier': card.metadata.get('reward_value_multiplier', 0.01)
                        }
            
            # Calculate spending rewards using ONLY the best rate per category
            for category_slug, annual_spend in spending_by_category.items():
                if category_slug in category_allocated:
                    allocation = category_allocated[category_slug]
                    rate = allocation['rate']
                    max_spend = allocation['max_spend']
                    multiplier = allocation['multiplier']
                    
                    # Apply spending caps
                    effective_spend = annual_spend
                    if max_spend:
                        effective_spend = min(annual_spend, float(max_spend))
                    
                    # Calculate rewards: spend * rate * value_multiplier
                    category_rewards = effective_spend * rate * float(multiplier)
                    total_value += category_rewards
            
            return total_value - total_fees
        
                 # Try different combinations to find optimal portfolio
        best_combination = []
        best_value = 0  # Start with $0 - only accept positive portfolio values!
        
        # Always include current cards (keeps) - let portfolio optimization decide profitability
        must_include = [cd for cd in card_scores if cd['action'] == 'keep']
        remaining_cards = [cd for cd in card_scores if cd not in must_include]
        
        print(f"DEBUG: Portfolio optimization - must_include: {len(must_include)}, remaining: {len(remaining_cards)}, max_cards: {max_cards}")
        
        # Start with empty portfolio (value = $0) as baseline
        empty_portfolio_value = calculate_portfolio_value([])
        if empty_portfolio_value > best_value:
            best_value = empty_portfolio_value
            best_combination = []
            print(f"DEBUG: Empty portfolio baseline - value: ${best_value:.2f}")
        
        # Aggressive performance optimization - limit search space dramatically
        max_combinations = min(len(remaining_cards), max_cards - len(must_include))
        
        # Sort remaining cards by individual net value for smarter search
        remaining_cards.sort(key=lambda x: x['net_value'], reverse=True)
        
        # DEBUG: Show top cards being considered with efficiency scores
        print(f"DEBUG: Top 15 cards by net value (with efficiency scoring):")
        for i, card_data in enumerate(remaining_cards[:15]):
            base_val = card_data.get('base_net_value', card_data['net_value'])
            efficiency = card_data.get('efficiency_score', 0)
            boost = card_data.get('efficiency_boost', 0)
            print(f"  {i+1}. {card_data['card'].name}: ${card_data['net_value']:.0f} (base: ${base_val:.0f}, efficiency: {efficiency:.2f}, boost: +${boost:.0f})")
        
        # DEBUG: Specifically look for Amazon Prime card
        amazon_cards = [cd for cd in remaining_cards if 'Amazon' in cd['card'].name]
        if amazon_cards:
            print(f"DEBUG: Amazon cards with efficiency:")
            for i, card_data in enumerate(amazon_cards):
                base_val = card_data.get('base_net_value', card_data['net_value'])
                efficiency = card_data.get('efficiency_score', 0)
                boost = card_data.get('efficiency_boost', 0)
                print(f"  Amazon {i+1}. {card_data['card'].name}: ${card_data['net_value']:.0f} (base: ${base_val:.0f}, efficiency: {efficiency:.2f}, boost: +${boost:.0f})")
        else:
            print(f"DEBUG: No Amazon cards found in remaining_cards")
        
        # Only test top cards to limit exponential explosion
        cards_to_test = remaining_cards[:min(20, len(remaining_cards))]  # Top 20 cards to include relevant niche cards
        print(f"DEBUG: Testing top {len(cards_to_test)} cards for performance")
        
        # Try combinations of different sizes with strict limits
        for combo_size in range(0, min(max_combinations + 1, 4)):  # Max 3 new cards
            if len(must_include) + combo_size > max_cards:
                break
            
            combinations_tested = 0
            max_combinations_to_test = 30 if combo_size <= 2 else 10  # Fewer tests for larger combos
            
            for combination in combinations(cards_to_test, combo_size):
                combinations_tested += 1
                if combinations_tested > max_combinations_to_test:
                    print(f"DEBUG: Hit combination limit for size {combo_size}, moving to next size")
                    break
                
                full_combination = must_include + list(combination)
                # Convert to actions format for efficiency-enhanced portfolio calculation
                actions = [{'card': cd['card'], 'action': cd['action']} for cd in full_combination]
                portfolio_value = self._calculate_scenario_portfolio_value(actions)
                
                # Only accept portfolios with positive value
                if portfolio_value > best_value and portfolio_value > 0:
                    best_value = portfolio_value
                    best_combination = full_combination
                    print(f"DEBUG: New best combination - value: ${best_value:.2f}, cards: {[cd['card'].name for cd in best_combination]}")
        
        # If no positive portfolio found, return empty (no recommendations)
        if best_value <= 0:
            print(f"DEBUG: No profitable portfolio found - returning no recommendations")
            return []
        
        # Ensure we don't return more than max_cards
        return best_combination[:max_cards]
    
    def _generate_card_reasoning(self, card_data: dict) -> str:
        """Generate reasoning text for a card recommendation"""
        card = card_data['card']
        action = card_data['action']
        net_value = card_data['net_value']
        
        if action == 'apply':
            signup_bonus = self._get_signup_bonus_value(card)
            annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
            fee_text = " (first year fee waived)" if annual_fee_waived else f" (${card.annual_fee} annual fee)"
            if signup_bonus > 0:
                return f"Apply - adds ${net_value:.0f} annual value + ${signup_bonus:.0f} signup bonus{fee_text}"
            else:
                return f"Apply - adds ${net_value:.0f} annual value{fee_text}"
        elif action == 'keep':
            return f"Keep - provides ${net_value:.0f} annual value to portfolio"
        else:  # cancel
            return f"Cancel - redundant card providing negative portfolio value"
    
    def _select_best_new_cards(self, available_cards: List[CreditCard], max_new_cards: int) -> List[dict]:
        """Select best new cards to apply for"""
        actions = []
        card_scores = []
        
        for card in available_cards:
            if not self._is_eligible_for_card(card):
                continue
                
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus_value = self._get_signup_bonus_value(card)
            
            annual_fee = float(card.annual_fee)
            annual_fee_waived_first_year = card.metadata.get('annual_fee_waived_first_year', False)
            effective_annual_fee = 0 if annual_fee_waived_first_year else annual_fee
            
            net_annual_value = annual_rewards - effective_annual_fee
            total_value = net_annual_value + signup_bonus_value
            
            if total_value > 0:  # Only consider positive value cards
                card_scores.append({
                    'card': card,
                    'total_value': total_value,
                    'net_annual_value': net_annual_value,
                    'signup_bonus': signup_bonus_value,
                    'rewards_breakdown': rewards_breakdown['breakdown']
                })
        
        # Sort by total value and take top cards
        card_scores.sort(key=lambda x: x['total_value'], reverse=True)
        
        for i, card_data in enumerate(card_scores[:max_new_cards]):
            reasoning = f"Apply - ${card_data['total_value']:.0f} total value (${card_data['net_annual_value']:.0f} annual + ${card_data['signup_bonus']:.0f} signup bonus)"
            
            actions.append({
                'card': card_data['card'],
                'action': 'apply',
                'reasoning': reasoning,
                'priority': i + 10  # Lower priority than keep actions
            })
        
        return actions
    
    def _calculate_scenario_portfolio_value(self, actions: List[dict]) -> float:
        """Calculate net portfolio value for a scenario using fast portfolio optimization (no double counting)"""
        portfolio_cards = [action for action in actions if action['action'] in ['keep', 'apply']]
        
        if not portfolio_cards:
            return 0.0
        
        # Calculate total annual fees
        total_annual_fees = 0
        total_signup_bonuses = 0
        
        for action in portfolio_cards:
            card = action['card']
            if action['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                total_annual_fees += 0  # First year waived
            else:
                total_annual_fees += float(card.annual_fee)
            
            # Add signup bonus for new cards
            if action['action'] == 'apply':
                total_signup_bonuses += self._get_signup_bonus_value(card)
        
        # Use cached spending data for performance
        if not hasattr(self, '_cached_parent_spending'):
            self._cached_parent_spending = self._build_parent_category_spending()
        
        parent_category_spending = self._cached_parent_spending
        
        # Fast category optimization: find best rate per category
        category_best_rates = {}
        
        for action in portfolio_cards:
            card = action['card']
            # Pre-fetch all reward categories to avoid N+1 queries
            if not hasattr(card, '_cached_reward_categories'):
                card._cached_reward_categories = list(card.reward_categories.filter(is_active=True).select_related('category'))
            
            for reward_category in card._cached_reward_categories:
                category_slug = reward_category.category.slug
                reward_rate = float(reward_category.reward_rate)
                
                # Only consider categories where user has spending
                if parent_category_spending.get(category_slug, 0) > 0:
                    if category_slug not in category_best_rates or reward_rate > category_best_rates[category_slug]['rate']:
                        category_best_rates[category_slug] = {
                            'rate': reward_rate,
                            'card': card,
                            'max_spend': reward_category.max_annual_spend
                        }
        
        # Calculate portfolio rewards using ONLY the best rate for each category
        total_portfolio_rewards = 0
        allocated_spending = 0
        
        for category_slug, rate_data in category_best_rates.items():
            annual_spend = parent_category_spending.get(category_slug, 0.0)
            
            if annual_spend > 0:
                # Apply spending caps
                if rate_data['max_spend']:
                    annual_spend = min(annual_spend, float(rate_data['max_spend']))
                
                allocated_spending += annual_spend
                reward_rate = rate_data['rate']
                best_card = rate_data['card']
                
                reward_value_multiplier = best_card.metadata.get('reward_value_multiplier', 0.01)
                points_earned = annual_spend * reward_rate
                category_rewards = points_earned * float(reward_value_multiplier)
                total_portfolio_rewards += category_rewards
        
        # Handle unallocated spending with best general category (simplified)
        total_parent_spending = sum(parent_category_spending.values())
        unallocated_spending = total_parent_spending - allocated_spending
        
        if unallocated_spending > 0:
            # Find best general rate among portfolio cards
            best_general_rate = 1.0  # Default base rate
            best_general_multiplier = 0.01
            
            for action in portfolio_cards:
                card = action['card']
                for reward_category in card._cached_reward_categories:
                    if reward_category.category.slug in ['general', 'other', 'everything-else']:
                        rate = float(reward_category.reward_rate)
                        if rate > best_general_rate:
                            best_general_rate = rate
                            best_general_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
            
            general_rewards = unallocated_spending * best_general_rate * float(best_general_multiplier)
            total_portfolio_rewards += general_rewards
        
        base_portfolio_value = total_portfolio_rewards + total_signup_bonuses - total_annual_fees
        
        # Add efficiency bonus: boost portfolios that include highly relevant cards
        total_efficiency_boost = 0
        for action in portfolio_cards:
            card = action['card']
            efficiency_score = self._calculate_spending_efficiency(card)
            
            if efficiency_score > 0.1:  # Boost any somewhat relevant cards (lowered threshold)
                card_annual_value = self._calculate_smart_card_value(card, signup_bonus=False) - float(card.annual_fee)
                card_signup_value = self._get_signup_bonus_value(card) if action['action'] == 'apply' else 0
                card_base_value = card_annual_value + card_signup_value
                efficiency_boost = card_base_value * efficiency_score * 0.5  # 50% max boost for perfect efficiency
                total_efficiency_boost += efficiency_boost
        
        final_value = base_portfolio_value + total_efficiency_boost
        
        return final_value
    
    def _build_parent_category_spending(self) -> dict:
        """Build and cache parent category spending map for performance"""
        all_spending = {}
        
        # Get spending amounts
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            all_spending[category_slug] = annual_spend
        
        # Build parent category spending map
        from cards.models import SpendingCategory
        parent_category_spending = {}
        
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
        
        return parent_category_spending
    
    def _calculate_smart_card_value(self, card: CreditCard, signup_bonus: bool = True) -> float:
        """Calculate card value considering actual user spending and category competition"""
        if not hasattr(self, '_cached_parent_spending'):
            self._cached_parent_spending = self._build_parent_category_spending()
        
        parent_category_spending = self._cached_parent_spending
        total_rewards = 0
        
        # Pre-fetch reward categories to avoid N+1 queries
        if not hasattr(card, '_cached_reward_categories'):
            card._cached_reward_categories = list(card.reward_categories.filter(is_active=True).select_related('category'))
        
        # Calculate rewards for categories where user actually spends money
        for reward_category in card._cached_reward_categories:
            category_slug = reward_category.category.slug
            
            # Check both parent category spending AND direct subcategory spending
            annual_spend = parent_category_spending.get(category_slug, 0.0)
            
            # If no parent spending found, check if this is a subcategory with direct spending
            if annual_spend == 0:
                # Get original spending amounts for subcategories
                for orig_category_slug, monthly_amount in self.spending_amounts.items():
                    if orig_category_slug == category_slug:
                        annual_spend = float(monthly_amount) * 12
                        break
            
            if annual_spend > 0:  # Only calculate for categories with actual spending
                reward_rate = float(reward_category.reward_rate)
                
                # Apply spending caps
                effective_spend = annual_spend
                if reward_category.max_annual_spend:
                    effective_spend = min(annual_spend, float(reward_category.max_annual_spend))
                
                # Calculate rewards: spend * rate * value_multiplier
                reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
                category_rewards = effective_spend * reward_rate * float(reward_value_multiplier)
                total_rewards += category_rewards
        
        # Add signup bonus if requested
        if signup_bonus:
            signup_value = self._get_signup_bonus_value(card)
            total_rewards += signup_value
        
        return total_rewards
    
    def _calculate_spending_efficiency(self, card: CreditCard) -> float:
        """Calculate how efficiently a card matches user's actual spending pattern
        
        Returns a score from 0.0 to 1.0 where:
        - 1.0 = Perfect match (high rewards for categories where user spends most)
        - 0.5 = Average (some relevant categories)
        - 0.0 = No match (no rewards for user's spending categories)
        """
        if not hasattr(self, '_cached_parent_spending'):
            self._cached_parent_spending = self._build_parent_category_spending()
        
        parent_category_spending = self._cached_parent_spending
        total_user_spending = sum(parent_category_spending.values())
        
        if total_user_spending == 0:
            return 0.0
        
        # Pre-fetch reward categories
        if not hasattr(card, '_cached_reward_categories'):
            card._cached_reward_categories = list(card.reward_categories.filter(is_active=True).select_related('category'))
        
        relevant_spending = 0.0
        weighted_efficiency = 0.0
        
        for reward_category in card._cached_reward_categories:
            category_slug = reward_category.category.slug
            
            # Check both parent category spending AND direct subcategory spending
            annual_spend = parent_category_spending.get(category_slug, 0.0)
            
            # If no parent spending found, check subcategory spending
            if annual_spend == 0:
                for orig_category_slug, monthly_amount in self.spending_amounts.items():
                    if orig_category_slug == category_slug:
                        annual_spend = float(monthly_amount) * 12
                        break
            
            if annual_spend > 0:
                reward_rate = float(reward_category.reward_rate)
                spending_weight = annual_spend / total_user_spending
                
                # Efficiency = reward rate above baseline (1x = no efficiency, 5x = high efficiency)
                efficiency = max(0, (reward_rate - 1.0) / 4.0)  # Normalize to 0-1 scale
                efficiency = min(1.0, efficiency)  # Cap at 1.0
                
                weighted_efficiency += efficiency * spending_weight
                relevant_spending += annual_spend
        
        # Bonus for coverage: how much of user's spending does this card address?
        coverage_ratio = relevant_spending / total_user_spending
        
        # Final efficiency score combines reward efficiency and spending coverage
        final_score = (weighted_efficiency * 0.7) + (coverage_ratio * 0.3)
        return min(1.0, final_score)
    
    def _find_new_cards(self, eligible_cards: List[CreditCard], max_cards: int) -> List[dict]:
        """Find best new cards to apply for"""
        recommendations = []
        
        # Remove cards user already has
        current_card_ids = {uc.card.id for uc in self.user_cards}
        available_cards = [c for c in eligible_cards if c.id not in current_card_ids]
        
        # Score cards by potential value
        card_scores = []
        for card in available_cards:
            if not self._is_eligible_for_card(card):
                continue
                
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus_value = self._get_signup_bonus_value(card)
            
            # Check if annual fee is waived first year for new applications
            annual_fee = float(card.annual_fee)
            annual_fee_waived_first_year = card.metadata.get('annual_fee_waived_first_year', False)
            effective_annual_fee = 0 if annual_fee_waived_first_year else annual_fee
            
            # Scoring: use annual rewards only (no signup bonus) for consistency with owned cards
            annual_value = annual_rewards - effective_annual_fee
            
            # Include signup bonus in total value assessment for filtering
            total_value = annual_value + signup_bonus_value
            
            # Only consider cards with non-negative total estimated value (including signup bonus)
            if total_value >= 0:
                card_scores.append({
                    'card': card,
                    'score': annual_value,
                    'annual_rewards': annual_rewards,
                    'signup_bonus': signup_bonus_value,
                    'rewards_breakdown': rewards_breakdown['breakdown'],
                    'reasoning': f"Annual value: ${annual_value:.0f} (${annual_rewards:.0f} rewards - ${effective_annual_fee} fee{' - first year fee waived' if annual_fee_waived_first_year else ''}) + ${signup_bonus_value:.0f} signup bonus"
                })
        
        # Sort by score and take top cards
        card_scores.sort(key=lambda x: x['score'], reverse=True)
        
        for i, card_data in enumerate(card_scores[:max_cards]):
            # For new card recommendations, include signup bonus in estimated rewards
            total_estimated_value = card_data['score'] + card_data['signup_bonus']
            
            recommendations.append({
                'card': card_data['card'],
                'action': 'apply',
                'estimated_rewards': Decimal(str(total_estimated_value)),
                'reasoning': card_data['reasoning'],
                'rewards_breakdown': card_data['rewards_breakdown'],
                'priority': i + 1
            })
        
        return recommendations
    
    def _is_eligible_for_card(self, card: CreditCard) -> bool:
        """Check if user is eligible for card based on issuer policies"""
        issuer = card.issuer
        
        # Check issuer-specific rules
        if issuer.name.lower() == 'chase':
            # Simplified 5/24 rule check
            # Only count cards with known opening dates
            recent_cards = UserCard.objects.filter(
                profile=self.profile,
                opened_date__isnull=False,
                opened_date__gte=datetime.now().date() - timedelta(days=24*30)
            ).count()
            
            if recent_cards >= 5:
                return False
        
        # Check if user already has this exact card
        if UserCard.objects.filter(profile=self.profile, card=card, is_active=True).exists():
            return False
        
        return True
    
    def _calculate_card_annual_rewards(self, card: CreditCard) -> float:
        """Calculate annual rewards for a card based on user spending"""
        breakdown = self._calculate_card_rewards_breakdown(card)
        return breakdown['total_rewards']
    
    def _calculate_card_rewards_breakdown(self, card: CreditCard) -> dict:
        """Calculate detailed rewards breakdown for a card"""
        total_rewards = 0.0
        breakdown_details = []
        
        # Get the card's reward value multiplier (how much each point/mile is worth)
        reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
        
        # Create a map of spending by category slug and also track all spending
        all_spending = {}
        total_spending = 0.0
        
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            all_spending[category_slug] = annual_spend
            total_spending += annual_spend
        
        # Build a map of parent category spending by aggregating subcategory spending
        from cards.models import SpendingCategory
        parent_category_spending = {}
        
        # For each spending category, if it's a subcategory, add its spending to the parent
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    # This is a subcategory, add its spending to the parent
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    # This is a parent category, include its direct spending
                    parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                # Category doesn't exist in database, treat as parent category
                parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
        
        # Track which spending has been allocated to specific reward categories
        allocated_spending = 0.0
        
        # Calculate rewards for specific reward categories
        for reward_category in card.reward_categories.filter(is_active=True):
            category_slug = reward_category.category.slug
            
            # Check if this reward category applies to a parent category that has aggregated spending
            annual_spend = parent_category_spending.get(category_slug, 0.0)
            
            if annual_spend > 0:  # Only include categories with spending
                # Apply spending caps if they exist
                if reward_category.max_annual_spend:
                    annual_spend = min(annual_spend, float(reward_category.max_annual_spend))
                
                allocated_spending += annual_spend
                reward_rate = float(reward_category.reward_rate)
                # Calculate points/miles earned: spend * rate
                points_earned = annual_spend * reward_rate
                # Convert to cash value using card's specific multiplier
                category_rewards = points_earned * float(reward_value_multiplier)
                total_rewards += category_rewards
                
                # Add to breakdown
                breakdown_details.append({
                    'category_name': reward_category.category.display_name or reward_category.category.name,
                    'monthly_spend': annual_spend / 12,
                    'annual_spend': annual_spend,
                    'reward_rate': reward_rate,
                    'reward_multiplier': float(reward_value_multiplier),
                    'points_earned': points_earned,
                    'category_rewards': category_rewards,
                    'calculation': f"${annual_spend:,.0f} × {reward_rate:.1f}x × {float(reward_value_multiplier):.3f} = ${category_rewards:.2f}"
                })
        
        # Handle unallocated spending - apply to general category if it exists
        # Use the total spending from parent categories (not subcategories)
        total_parent_spending = sum(parent_category_spending.values())
        unallocated_spending = total_parent_spending - allocated_spending
        if unallocated_spending > 0:
            # Look for a general/catch-all category
            general_category = card.reward_categories.filter(
                is_active=True, 
                category__slug__in=['general', 'other', 'everything-else']
            ).first()
            
            if general_category:
                reward_rate = float(general_category.reward_rate)
                points_earned = unallocated_spending * reward_rate
                category_rewards = points_earned * float(reward_value_multiplier)
                total_rewards += category_rewards
                
                breakdown_details.append({
                    'category_name': 'Other Spending',
                    'monthly_spend': unallocated_spending / 12,
                    'annual_spend': unallocated_spending,
                    'reward_rate': reward_rate,
                    'reward_multiplier': float(reward_value_multiplier),
                    'points_earned': points_earned,
                    'category_rewards': category_rewards,
                    'calculation': f"${unallocated_spending:,.0f} × {reward_rate:.1f}x × {float(reward_value_multiplier):.3f} = ${category_rewards:.2f}"
                })
        
        # Add card credits to the total rewards if user has selected them
        credits_value, credits_breakdown = self._calculate_card_credits_value(card)
        total_rewards += credits_value
        
        if credits_value > 0:
            breakdown_details.append({
                'category_name': 'Card Benefits & Credits',
                'monthly_spend': 0,
                'annual_spend': 0,
                'reward_rate': 0,
                'reward_multiplier': 1.0,
                'points_earned': credits_value,
                'category_rewards': credits_value,
                'calculation': f"Selected card benefits worth ${credits_value:.2f} annually",
                'credits_breakdown': credits_breakdown
            })
        
        return {
            'total_rewards': total_rewards,
            'breakdown': breakdown_details,
            'reward_multiplier': float(reward_value_multiplier)
        }
    
    def _get_signup_bonus_value(self, card: CreditCard) -> float:
        """Get signup bonus value using card's specific reward value multiplier"""
        if card.signup_bonus_amount:
            # Check signup bonus type to determine if conversion is needed
            signup_bonus_type = getattr(card, 'signup_bonus_type', None)
            
            if signup_bonus_type and hasattr(signup_bonus_type, 'name'):
                bonus_type_name = signup_bonus_type.name.lower()
            elif signup_bonus_type:
                bonus_type_name = str(signup_bonus_type).lower()
            else:
                bonus_type_name = 'unknown'
            
            if bonus_type_name in ['cashback', 'cash', 'cash back']:
                # Cashback signup bonuses are already in dollars
                bonus_value = float(card.signup_bonus_amount)
                
                # Sanity check: If cashback bonus > $5000, it's probably misclassified points
                if bonus_value > 5000:
                    # Treat as points with conversion
                    reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
                    bonus_value = bonus_value * float(reward_value_multiplier)
                    if bonus_value > 10000:  # Still too high, cap it
                        bonus_value = min(bonus_value, 10000)
                
                return bonus_value
            else:
                # Points/miles need to be converted using reward value multiplier
                reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
                bonus_value = float(card.signup_bonus_amount) * float(reward_value_multiplier)
                return bonus_value
        return 0.0
    
    def _calculate_card_credits_value(self, card: CreditCard) -> tuple[float, list]:
        """Calculate the annual value of card credits that user has selected as valuable
        
        Returns:
            tuple: (total_credits_value, credits_breakdown)
            credits_breakdown is a list of dicts with credit details
        """
        credits_value = 0.0
        credits_breakdown = []
        
        # Get user's selected spending credit preferences
        user_spending_credit_preferences = set()
        if hasattr(self.profile, 'spending_credit_preferences'):
            user_spending_credit_preferences = set(
                pref.spending_credit.slug 
                for pref in self.profile.spending_credit_preferences.filter(values_credit=True)
            )
        
        # Get user's spending categories (for category-based credits)
        user_spending_categories = set(
            spending.category.slug
            for spending in self.profile.spending_amounts.all()
            if spending.monthly_amount > 0
        )
        
        # Calculate value of card credits that match user preferences
        for card_credit in card.credits.filter(is_active=True):
            credit_matches = False
            credit_type = None
            credit_name = None
            
            # Check spending_credit system
            if card_credit.spending_credit and card_credit.spending_credit.slug in user_spending_credit_preferences:
                credit_matches = True
                credit_type = "benefit"
                credit_name = card_credit.spending_credit.display_name
            
            # Check category-based credits (automatically include if spending in that category)
            elif card_credit.category and card_credit.category.slug in user_spending_categories:
                credit_matches = True
                credit_type = "category"
                credit_name = f"{card_credit.category.display_name} Credit"
            
            if credit_matches:
                # Calculate annual value (value * times_per_year)
                annual_value = float(card_credit.value) * card_credit.times_per_year
                credits_value += annual_value
                
                # Add to breakdown
                frequency_text = ""
                if card_credit.times_per_year > 1:
                    frequency_text = f" (${card_credit.value} × {card_credit.times_per_year}/year)"
                
                credits_breakdown.append({
                    'name': credit_name or card_credit.description,
                    'value': float(card_credit.value),
                    'times_per_year': card_credit.times_per_year,
                    'annual_value': annual_value,
                    'type': credit_type,
                    'description': card_credit.description,
                    'frequency_display': frequency_text
                })
        
        return credits_value, credits_breakdown
    
    def _calculate_total_rewards(self, recommendations: List[Dict]) -> Decimal:
        """Calculate total estimated rewards from all recommendations"""
        total = sum(rec.get('estimated_rewards', 0) for rec in recommendations)
        return Decimal(str(total))
    
    def _calculate_portfolio_summary(self, recommendations: List[dict]) -> dict:
        """Calculate portfolio-optimized summary considering card overlap and total fees"""
        if not recommendations:
            return {
                'total_annual_fees': 0,
                'total_portfolio_rewards': 0,
                'net_portfolio_value': 0,
                'category_optimization': {},
                'card_count': 0
            }
        
        # Separate cards by action type
        cards_to_keep = []
        cards_to_apply = []
        
        for rec in recommendations:
            if rec['action'] in ['keep', 'apply']:
                card_data = {
                    'card': rec['card'],
                    'action': rec['action'],
                    'rewards_breakdown': rec.get('rewards_breakdown', [])
                }
                if rec['action'] == 'keep':
                    cards_to_keep.append(card_data)
                else:  # apply
                    cards_to_apply.append(card_data)
        
        all_portfolio_cards = cards_to_keep + cards_to_apply
        
        # Calculate total annual fees
        total_annual_fees = 0
        for card_data in all_portfolio_cards:
            card = card_data['card']
            if card_data['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                # First year fee is waived for new applications
                total_annual_fees += 0
            else:
                total_annual_fees += float(card.annual_fee)
        
        # Initialize category optimization map (will be built after spending calculation)
        category_optimization = {}
        
        # Calculate PROPERLY OPTIMIZED portfolio rewards (no double counting)
        total_portfolio_rewards = 0
        allocated_spending = 0
        
        # Create spending map
        all_spending = {}
        print(f"DEBUG: self.spending_amounts in portfolio summary: {dict(self.spending_amounts)}")
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            all_spending[category_slug] = annual_spend
            print(f"DEBUG: {category_slug}: ${monthly_amount}/month -> ${annual_spend}/year")
        
        # Build parent category spending map
        from cards.models import SpendingCategory
        parent_category_spending = {}
        
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
        
        # Calculate rewards using ONLY the best rate for each category (avoiding double counting)
        allocated_categories = set()
        
        for category_slug, optimization_data in category_optimization.items():
            if category_slug in allocated_categories:
                continue  # Skip if already allocated
                
            annual_spend = parent_category_spending.get(category_slug, 0.0)
            
            if annual_spend > 0:
                # Apply spending caps
                if optimization_data['max_annual_spend']:
                    annual_spend = min(annual_spend, float(optimization_data['max_annual_spend']))
                
                allocated_spending += annual_spend
                allocated_categories.add(category_slug)
                reward_rate = optimization_data['best_rate']
                
                # Get the reward value multiplier from the best card
                best_card = None
                for card_data in all_portfolio_cards:
                    if card_data['card'].name == optimization_data['best_card']:
                        best_card = card_data['card']
                        break
                
                if best_card:
                    reward_value_multiplier = best_card.metadata.get('reward_value_multiplier', 0.01)
                    points_earned = annual_spend * reward_rate
                    category_rewards = points_earned * float(reward_value_multiplier)
                    total_portfolio_rewards += category_rewards
                    
                    # Update optimization data
                    category_optimization[category_slug]['annual_spend'] = annual_spend
                    category_optimization[category_slug]['annual_rewards'] = category_rewards
        
        # Handle unallocated spending with best general category 
        total_parent_spending = sum(parent_category_spending.values())
        unallocated_spending = total_parent_spending - allocated_spending
        print(f"DEBUG: parent_category_spending: {parent_category_spending}")
        print(f"DEBUG: total_parent_spending: ${total_parent_spending} (type: {type(total_parent_spending)})")
        print(f"DEBUG: allocated_spending: ${allocated_spending}")
        print(f"DEBUG: unallocated_spending: ${unallocated_spending}")
        
        if unallocated_spending > 0:
            # Find best general category across all portfolio cards
            best_general_rate = 0
            best_general_card = None
            
            for card_data in all_portfolio_cards:
                card = card_data['card']
                general_category = card.reward_categories.filter(
                    is_active=True, 
                    category__slug__in=['general', 'other', 'everything-else']
                ).first()
                
                if general_category:
                    rate = float(general_category.reward_rate)
                    if rate > best_general_rate:
                        best_general_rate = rate
                        best_general_card = card
            
            if best_general_card and best_general_rate > 0:
                reward_value_multiplier = best_general_card.metadata.get('reward_value_multiplier', 0.01)
                points_earned = unallocated_spending * best_general_rate
                general_rewards = points_earned * float(reward_value_multiplier)
                total_portfolio_rewards += general_rewards
                
                # Add to category optimization
                category_optimization['other_spending'] = {
                    'category_name': 'Other Spending',
                    'best_rate': best_general_rate,
                    'best_card': best_general_card.name,
                    'annual_spend': unallocated_spending,
                    'annual_rewards': general_rewards,
                    'max_annual_spend': None
                }
        
        # Build category optimization map for categories with spending > 0 and rate > 1x
        for card_data in all_portfolio_cards:
            card = card_data['card']
            for reward_category in card.reward_categories.filter(is_active=True):
                category_slug = reward_category.category.slug
                category_name = reward_category.category.display_name or reward_category.category.name
                reward_rate = float(reward_category.reward_rate)
                
                # Only include if user has spending in this category AND rate > 1x
                annual_spend = parent_category_spending.get(category_slug, 0.0)
                if annual_spend > 0 and reward_rate > 1.0:
                    if category_slug not in category_optimization:
                        category_optimization[category_slug] = {
                            'category_name': category_name,
                            'best_rate': reward_rate,
                            'best_card': card.name,
                            'max_annual_spend': reward_category.max_annual_spend,
                            'annual_spend': annual_spend
                        }
                    else:
                        # Update if this card has a better rate
                        if reward_rate > category_optimization[category_slug]['best_rate']:
                            category_optimization[category_slug].update({
                                'best_rate': reward_rate,
                                'best_card': card.name,
                                'max_annual_spend': reward_category.max_annual_spend,
                                'annual_spend': annual_spend
                            })
                        # If same rate but higher spending cap, prefer this card
                        elif (reward_rate == category_optimization[category_slug]['best_rate'] and
                              reward_category.max_annual_spend and
                              (not category_optimization[category_slug]['max_annual_spend'] or
                               float(reward_category.max_annual_spend) > float(category_optimization[category_slug]['max_annual_spend'] or 0))):
                            category_optimization[category_slug].update({
                                'best_card': card.name,
                                'max_annual_spend': reward_category.max_annual_spend,
                                'annual_spend': annual_spend
                            })
        
        # Filter out "other_spending" if rate is 1x or no spending
        if 'other_spending' in category_optimization:
            other_data = category_optimization['other_spending']
            if other_data.get('best_rate', 0) <= 1.0 or other_data.get('annual_spend', 0) <= 0:
                del category_optimization['other_spending']
        
        # Add card benefits/credits (avoid double counting by using set of unique credits)
        unique_credits = set()
        total_credits_value = 0
        
        # Get user preferences for spending credits
        user_spending_credit_preferences = set()
        if hasattr(self.profile, 'spending_credit_preferences'):
            user_spending_credit_preferences = set(
                pref.spending_credit.slug 
                for pref in self.profile.spending_credit_preferences.filter(values_credit=True)
            )
        
        user_spending_categories = set(
            spending.category.slug
            for spending in self.profile.spending_amounts.all()
            if spending.monthly_amount > 0
        )
        
        for card_data in all_portfolio_cards:
            card = card_data['card']
            for card_credit in card.credits.filter(is_active=True):
                credit_key = None
                credit_matches = False
                
                # Check spending_credit system
                if card_credit.spending_credit and card_credit.spending_credit.slug in user_spending_credit_preferences:
                    credit_key = f"spending_credit_{card_credit.spending_credit.slug}"
                    credit_matches = True
                
                # Check category-based credits
                elif card_credit.category and card_credit.category.slug in user_spending_categories:
                    credit_key = f"category_{card_credit.category.slug}"
                    credit_matches = True
                
                # Add credit value if it matches and we haven't counted this credit type yet
                if credit_matches and credit_key and credit_key not in unique_credits:
                    unique_credits.add(credit_key)
                    annual_value = float(card_credit.value) * card_credit.times_per_year
                    total_credits_value += annual_value
        
        total_portfolio_rewards += total_credits_value
        
        # Add signup bonuses for new card applications
        total_signup_bonuses = 0
        for card_data in all_portfolio_cards:
            if card_data['action'] == 'apply':
                signup_bonus = self._get_signup_bonus_value(card_data['card'])
                total_signup_bonuses += signup_bonus
        
        total_portfolio_rewards += total_signup_bonuses
        print(f"DEBUG: Portfolio Summary - signup bonuses: ${total_signup_bonuses:.2f}")
        
        # Calculate net portfolio value (rewards - fees)
        net_portfolio_value = total_portfolio_rewards - total_annual_fees
        
        # ENSURE NET VALUE IS NEVER NEGATIVE by design
        # If negative, it means the optimization failed - this should not happen
        # with proper portfolio optimization, but let's log it for debugging
        if net_portfolio_value < 0:
            print(f"WARNING: Portfolio optimization resulted in negative value: ${net_portfolio_value:.2f}")
            print(f"Total rewards: ${total_portfolio_rewards:.2f}, Total fees: ${total_annual_fees:.2f}")
            print(f"Portfolio cards: {len(all_portfolio_cards)}")
            # In production, we might want to return an error or try a different optimization strategy
        
        # Create a summary that includes filtered recommendations
        result = {
            'total_annual_fees': total_annual_fees,
            'total_portfolio_rewards': total_portfolio_rewards,
            'net_portfolio_value': net_portfolio_value,
            'category_optimization': category_optimization,
            'card_count': len(all_portfolio_cards),
            'total_credits_value': total_credits_value,
            'total_annual_spending': total_parent_spending,
            'category_optimization_cards': {cat_data['best_card'] for cat_data in category_optimization.values()}
        }
        return result
    

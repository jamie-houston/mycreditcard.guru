import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from cards.models import CreditCard, UserSpendingProfile, UserCard
from roadmaps.models import Roadmap

logger = logging.getLogger(__name__)

class RecommendationEngineOrchestrator:
    """
    Core recommendation engine that coordinates:
    - User spending patterns
    - Issuer policies (5/24 rule, etc.)
    - Reward optimization
    - Annual fee vs. benefits analysis
    """
    
    # A year of bonus-earning capacity: counted signup bonuses consume
    # months of the user's total spending (see _bonus_months_needed).
    BONUS_CAPACITY_MONTHS = 12.0

    def __init__(self, profile: UserSpendingProfile, user_cards_data=None, strategy=None):
        from roadmaps.strategies import strategy_weights
        self.profile = profile
        self.strategy = strategy
        self.weights = strategy_weights(strategy)
        self.today = date.today()

        if profile.user:
            self.card_history = list(
                profile.user.owned_cards.select_related('card__issuer').all())
            self.user_cards = [uc for uc in self.card_history
                               if uc.closed_date is None]
        else:
            self.card_history = []
            self.user_cards = []

        if user_cards_data and not profile.user:
            from django.utils.dateparse import parse_date
            mock_user_cards = []
            for card_data in user_cards_data:
                try:
                    card = CreditCard.objects.get(id=card_data['card_id'])
                    mock_card = type('MockUserCard', (), {
                        'card': card,
                        'opened_date': parse_date(card_data.get('opened_date', '2020-01-01')),
                        'closed_date': None if card_data.get('is_active', True) else parse_date(card_data.get('opened_date', '2020-01-01')),
                        'nickname': card_data.get('nickname', ''),
                        'bonus_earned_date': parse_date(card_data['bonus_earned_date']) if card_data.get('bonus_earned_date') else None,
                        'bonus_override': card_data.get('bonus_override'),
                        'owner_id': None,
                    })()
                    mock_user_cards.append(mock_card)
                except CreditCard.DoesNotExist:
                    continue
            self.card_history = mock_user_cards
            self.user_cards = [uc for uc in mock_user_cards
                               if uc.closed_date is None]

        if profile.user:
            self.entities = list(profile.entities.all())
            if not self.entities:
                self.entities = [profile.primary_entity()]
            self._primary_entity = next(
                (e for e in self.entities if e.is_primary), self.entities[0])
        else:
            from types import SimpleNamespace
            self._primary_entity = SimpleNamespace(
                id=None, name='You', kind='personal', is_primary=True)
            self.entities = [self._primary_entity]

        self.entity_histories = {e.id: [] for e in self.entities}
        for uc in self.card_history:
            owner_id = getattr(uc, 'owner_id', None)
            if owner_id is None:
                owner_id = self._primary_entity.id
            self.entity_histories.setdefault(owner_id, []).append(uc)

        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount
            for sa in profile.spending_amounts.all()
        }
        self._card_credits_cache = {}
        self._credit_prefs = None
        self._credit_spending_categories = None

        from roadmaps.engine.eligibility_manager import EligibilityManager
        self.eligibility_manager = EligibilityManager(self)

        from roadmaps.engine.calculators.credits import CreditsCalculator
        self.credits_calculator = CreditsCalculator(self)

        from roadmaps.engine.calculators.rewards import RewardsCalculator
        self.rewards_calculator = RewardsCalculator(self)

        from roadmaps.engine.calculators.bonus import BonusCapacityManager
        self.bonus_capacity_manager = BonusCapacityManager(self)

        from roadmaps.engine.optimizer import PortfolioOptimizer
        self.optimizer = PortfolioOptimizer(self)

        from roadmaps.engine.calculators.expense import ExpenseRecommender
        self.expense_recommender = ExpenseRecommender(self)

    def generate_quick_recommendations(self, roadmap: Roadmap) -> List[dict]:
        """Generate recommendations without saving to database (includes breakdowns)"""
        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount
            for sa in self.profile.spending_amounts.all()
        }
        self._card_credits_cache = {}
        self._credit_prefs = None
        self._credit_spending_categories = None
        logger.debug(f"Reloaded spending_amounts: {dict(self.spending_amounts)}")
        
        eligible_cards = self._get_filtered_cards(roadmap)
        recommendations = self._generate_portfolio_optimized_recommendations(eligible_cards, roadmap)
        
        apply_recommendations = [rec for rec in recommendations if rec['action'] == 'apply']
        total_annual_spending = sum(float(amount) * 12 for amount in self.spending_amounts.values())
        
        if not apply_recommendations and total_annual_spending > 30000:
            logger.debug(f"High spending (${total_annual_spending:.0f}/year) with no apply recommendations - adding fallback")
            fallback_rec = self._get_best_signup_bonus_card(eligible_cards)
            if fallback_rec:
                recommendations.append(fallback_rec)
                logger.debug(f"Added fallback recommendation: APPLY {fallback_rec['card'].name}")
        
        logger.debug(f"Generated {len(recommendations)} recommendations before filtering:")
        for rec in recommendations:
            logger.debug(f"  - {rec['action'].upper()}: {rec['card'].name} (priority: {rec['priority']})")
        
        keeps_and_applies = [rec for rec in recommendations if rec['action'] in ['keep', 'apply', 'upgrade', 'downgrade']]
        cancels = [rec for rec in recommendations if rec['action'] == 'cancel']
        
        zero_fee_keeps = [rec for rec in keeps_and_applies if rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0]
        other_keeps_applies = [rec for rec in keeps_and_applies if not (rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0)]
        
        applies = [rec for rec in other_keeps_applies if rec['action'] == 'apply']
        other_keeps = [rec for rec in other_keeps_applies if rec['action'] != 'apply']
        
        applies.sort(key=lambda x: x['priority'])
        other_keeps.sort(key=lambda x: x['priority'])
        
        current_card_actions = [rec for rec in other_keeps if rec['action'] in ['keep']] + cancels
        new_card_actions = applies
        
        filtered_other_keeps_applies = current_card_actions.copy()
        max_new_card_applications = roadmap.max_recommendations

        months_committed = 0.0
        deferred_applies = []
        timeline = []
        bonus_less_applies = []
        if new_card_actions:
            new_card_actions = [rec for rec in new_card_actions
                                if float(rec['estimated_rewards']) > 0]
            new_card_actions.sort(key=lambda x: x['priority'])
            selected_applies = []
            for rec in new_card_actions:
                if len(selected_applies) >= max_new_card_applications:
                    break
                months = (self._bonus_months_needed(rec['card'])
                          if float(rec.get('signup_bonus_value', 0)) > 0 else 0.0)
                if months_committed + months <= self.BONUS_CAPACITY_MONTHS:
                    months_committed += months
                    selected_applies.append(rec)
                else:
                    if float(rec.get('signup_bonus_value', 0)) > 0:
                        logger.warning(
                            f"Unexpected assembly-time deferral for {rec['card'].name}: "
                            f"signup_bonus_value=${float(rec['signup_bonus_value']):.0f} "
                            f"survived selection's capacity check but doesn't fit assembly's "
                            f"running total — selection/display divergence.")
                    logger.debug(
                        f"Deferring {rec['card'].name}: bonus needs "
                        f"{months:.1f} months of spending, only "
                        f"{self.BONUS_CAPACITY_MONTHS - months_committed:.1f} left this year")
                    deferred_applies.append(rec)
            filtered_other_keeps_applies.extend(selected_applies)

            sequencing_held_cards = (
                [rec['card'] for rec in current_card_actions if rec['action'] == 'keep']
                + [rec['card'] for rec in selected_applies])
            sequencing_program_multipliers = self._program_multipliers(sequencing_held_cards)
            sequence_plan = self._bonus_capacity_plan(
                [rec['card'] for rec in selected_applies], sequencing_program_multipliers)
            if abs(sequence_plan['months_committed'] - months_committed) > 0.05:
                logger.warning(
                    f"Sequencing plan months_committed "
                    f"({sequence_plan['months_committed']:.1f}) disagrees with "
                    f"assembly's running total ({months_committed:.1f}).")

            for rec in selected_applies:
                entry = sequence_plan['by_card_id'].get(rec['card'].id)
                is_bonus_less = (rec.get('bonus_deferred')
                                 or not float(rec.get('signup_bonus_value', 0)) > 0)
                if is_bonus_less:
                    rec['recommended_month'] = 0
                    rec['bonus_months_needed'] = 0.0
                    if rec.get('bonus_deferred') and entry and entry['counted']:
                        logger.warning(
                            f"{rec['card'].name} shows bonus_deferred but the "
                            f"final sequence plan counts its bonus — will "
                            f"self-heal on the next regeneration.")
                elif entry and entry['counted']:
                    rec['recommended_month'] = int(round(entry['start_month']))
                    rec['bonus_months_needed'] = round(entry['months'], 1)
                else:
                    logger.warning(
                        f"{rec['card'].name} has signup_bonus_value="
                        f"${float(rec.get('signup_bonus_value', 0)):.0f} but the final "
                        f"sequence plan doesn't count it — selection/display divergence.")
                    rec['recommended_month'] = 0
                    rec['bonus_months_needed'] = round(entry['months'], 1) if entry else 0.0

            timeline_entries = []
            for rec in selected_applies:
                entry = sequence_plan['by_card_id'].get(rec['card'].id)
                is_bonus_less = (rec.get('bonus_deferred')
                                 or not float(rec.get('signup_bonus_value', 0)) > 0)
                sort_key = (float('inf') if is_bonus_less
                           else (entry['start_month'] if entry else float('inf')))
                timeline_entries.append((sort_key, {
                    'card_name': rec['card'].name,
                    'recommended_month': rec.get('recommended_month', 0),
                    'months_needed': rec.get('bonus_months_needed', 0.0),
                    'bonus_counted': not is_bonus_less,
                }))
            timeline_entries.sort(key=lambda t: t[0])
            timeline = [item for _, item in timeline_entries]
            bonus_less_applies = [rec['card'].name for rec in selected_applies
                                  if rec.get('bonus_deferred')]

        recommendations = filtered_other_keeps_applies + zero_fee_keeps

        for rec in recommendations:
            if rec['action'] != 'apply':
                rec['recommended_month'] = None
                rec['bonus_months_needed'] = None
        
        for rec in recommendations:
            if rec['action'] == 'keep':
                estimated_value = float(rec['estimated_rewards'])
                annual_fee = float(rec['card'].annual_fee)
                if estimated_value < 0 and annual_fee > 0:
                    rec['action'] = 'cancel'
                    rec['reasoning'] = f"Cancel - losing money: ${estimated_value + annual_fee:.0f} rewards vs ${annual_fee:.0f} fee (net: ${estimated_value:.0f})"
        
        logger.debug(f"Smart filtering breakdown:")
        logger.debug(f"  - Other keeps/applies: {len(filtered_other_keeps_applies)}")
        logger.debug(f"  - Zero fee keeps: {len(zero_fee_keeps)}")
        actual_cancels = [rec for rec in recommendations if rec['action'] == 'cancel']
        logger.debug(f"  - Cancels: {len(actual_cancels)}")
        logger.debug(f"Final {len(recommendations)} recommendations after smart filtering:")
        for rec in recommendations:
            fee_info = f" (${rec['card'].annual_fee} fee)" if rec['action'] in ['keep', 'cancel'] else ""
            logger.debug(f"  - {rec['action'].upper()}: {rec['card'].name}{fee_info} (priority: {rec['priority']})")
        
        portfolio_summary = self._calculate_portfolio_summary(recommendations)

        portfolio_summary['bonus_capacity'] = {
            'total_monthly_spending': self._total_monthly_spending(),
            'months_committed': round(months_committed, 1),
            'capacity_months': self.BONUS_CAPACITY_MONTHS,
            'deferred_applies': [rec['card'].name for rec in deferred_applies],
            'timeline': timeline,
            'bonus_less_applies': bonus_less_applies,
        }
        
        for rec in recommendations:
            rec['portfolio_summary'] = portfolio_summary

        return recommendations
    
    def generate_roadmap(self, roadmap: Roadmap) -> List[dict]:
        """Generate recommendations and save them to the database"""
        from roadmaps.models import RoadmapRecommendation, RoadmapCalculation
        
        roadmap.recommendations.all().delete()
        recommendations = self.generate_quick_recommendations(roadmap)
        
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
        
        total_rewards = self._calculate_total_rewards(recommendations)
        calculation, _ = RoadmapCalculation.objects.update_or_create(
            roadmap=roadmap,
            defaults={
                'total_estimated_rewards': total_rewards,
                'calculation_data': {
                    'breakdown': [
                        {
                            'card_slug': rec['card'].slug,
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
        """Apply roadmap filters to get eligible cards."""
        from collections import defaultdict
        from django.db.models import Q

        queryset = CreditCard.objects.filter(is_active=True)

        filters_by_type = defaultdict(list)
        for filter_obj in roadmap.filters.all():
            filters_by_type[filter_obj.filter_type].append(filter_obj.value)

        for filter_type, values in filters_by_type.items():
            type_q = Q()
            for value in values:
                if filter_type == 'issuer':
                    type_q |= Q(issuer__name__icontains=value)
                elif filter_type == 'reward_type':
                    type_q |= Q(primary_reward_type__name__icontains=value)
                elif filter_type == 'card_type':
                    type_q |= Q(card_type=value)
                elif filter_type == 'annual_fee':
                    if '+' in value:
                        type_q |= Q(annual_fee__gte=Decimal(value.replace('+', '')))
                    elif '-' in value:
                        min_fee, max_fee = map(Decimal, value.split('-'))
                        type_q |= Q(annual_fee__gte=min_fee, annual_fee__lte=max_fee)
                    else:
                        type_q |= Q(annual_fee=Decimal(value))
            queryset = queryset.filter(type_q)
        
        all_cards = list(queryset.prefetch_related('reward_categories', 'credits'))
        active_cards = [card for card in all_cards if not card.metadata.get('discontinued', False)]
        return active_cards
    
    def _generate_portfolio_optimized_recommendations(self, eligible_cards: List[CreditCard], roadmap: Roadmap) -> List[dict]:
        """Generate portfolio-optimized recommendations considering all cards together"""
        recommendations = []
        current_cards = [uc.card for uc in self.user_cards]
        available_new_cards = [c for c in eligible_cards if c.id not in {card.id for card in current_cards}]
        
        logger.debug(f"User has {len(current_cards)} current cards:")
        for card in current_cards:
            logger.debug(f"  - {card.name}")
        logger.debug(f"Found {len(available_new_cards)} available new cards")
        logger.debug(f"Max recommendations allowed: {roadmap.max_recommendations}")
        logger.debug(f"Will scenario 1 use optimization? {len(current_cards) == 0}")
        logger.debug(f"Will scenario 2 use optimization? {True}")
        
        max_total_cards = len(current_cards) + roadmap.max_recommendations
        best_portfolio = self._find_optimal_portfolio(current_cards, available_new_cards, max_total_cards)

        actions_by_card = {}
        for card_action in best_portfolio:
            key = (card_action['card'].id, card_action['action'] == 'apply')
            existing = actions_by_card.get(key)
            if existing is None or (existing['action'] == 'cancel'
                                    and card_action['action'] in ('keep', 'apply')):
                actions_by_card[key] = card_action
        best_portfolio = list(actions_by_card.values())

        for card_action in list(best_portfolio):
            if card_action['action'] != 'keep':
                continue
            card = card_action['card']
            second_entity = self._eligible_entity_for_card(card)
            if second_entity is None:
                continue
            best_portfolio.append({
                'card': card,
                'action': 'apply',
                'priority': 500 + card.id,
                'duplicate_copy': True,
                'duplicate_copy_owner': self._holding_entity_for_card(card),
            })

        held_cards = [ca['card'] for ca in best_portfolio
                      if ca['action'] in ('keep', 'apply') and not ca.get('duplicate_copy')]
        portfolio_allocation = self._calculate_portfolio_allocation(held_cards)
        credit_allocation = self._allocate_portfolio_credits(held_cards)
        program_multipliers = self._program_multipliers(held_cards)
        program_best_cards = self._program_best_cards(held_cards)

        apply_cards = [ca['card'] for ca in best_portfolio if ca['action'] == 'apply']
        capacity_plan = self._bonus_capacity_plan(apply_cards, program_multipliers)
        self._last_capacity_plan = capacity_plan

        for card_action in best_portfolio:
            card = card_action['card']
            action = card_action['action']

            if action == 'cancel':
                cancel_allocation = self._calculate_portfolio_allocation(held_cards + [card])
                cancel_credit_allocation = self._allocate_portfolio_credits(held_cards + [card])
                cancel_program_multipliers = self._program_multipliers(held_cards + [card])
                cancel_program_best_cards = self._program_best_cards(held_cards + [card])
                rewards_breakdown = self._calculate_card_allocated_breakdown(
                    card, cancel_allocation, cancel_credit_allocation, cancel_program_multipliers)
                active_program_best_cards = cancel_program_best_cards
            elif card_action.get('duplicate_copy'):
                owner_entity = card_action.get('duplicate_copy_owner')
                owner_name = owner_entity.name if owner_entity else 'another entity'
                rewards_breakdown = {
                    'total_rewards': 0.0,
                    'reward_multiplier': self._own_multiplier(card),
                    'total_spending_on_card': 0,
                    'breakdown': [self._info_item(
                        f"Category rewards already earned on {owner_name}'s copy",
                        f"{card.name}'s category rewards are already counted via "
                        f"{owner_name}'s copy of this card — this application is "
                        f"valued on its signup bonus alone")],
                }
                active_program_best_cards = program_best_cards
            else:
                rewards_breakdown = self._calculate_card_allocated_breakdown(
                    card, portfolio_allocation, credit_allocation, program_multipliers)
                active_program_best_cards = program_best_cards
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            multiplier = rewards_breakdown['reward_multiplier']

            own_multiplier = self._own_multiplier(card)
            if multiplier > own_multiplier:
                program = card.points_program.slug if getattr(card, 'points_program_id', None) else (card.metadata or {}).get('points_program')
                best_card = active_program_best_cards.get(program)
                best_name = best_card.name if best_card else 'a program card'
                rewards_breakdown['breakdown'].append(self._info_item(
                    f"Points valued via {best_name}",
                    f"{card.name}'s points valued at {multiplier * 100:.2f}¢ each "
                    f"(redeemed via {best_name}) instead of {own_multiplier * 100:.2f}¢ on its own"))

            eligibility_note = ''
            bonus_deferred = False
            if action == 'apply':
                signup_bonus_value = self._get_signup_bonus_value(card, program_multipliers)
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else annual_fee
                ongoing_value = annual_rewards - annual_fee

                bonus_block = self._bonus_ineligibility_note(card)
                capacity_entry = capacity_plan['by_card_id'].get(card.id)
                if bonus_block:
                    eligibility_note = bonus_block
                    signup_bonus_value = 0
                    plan = {'items': [self._info_item(
                        'Signup bonus not counted', bonus_block)],
                        'value_delta': 0.0, 'bonus_earnable': False}
                elif (capacity_entry is not None and not capacity_entry['counted']
                      and signup_bonus_value > 0):
                    bonus_deferred = True
                    signup_bonus_value = 0
                    plan = {'items': [self._info_item(
                        'Signup bonus deferred',
                        "Doesn't fit this year's bonus capacity at your "
                        "spending level — card recommended on ongoing value; "
                        "earn the bonus next year")],
                        'value_delta': 0.0, 'bonus_earnable': False}
                elif card_action.get('duplicate_copy'):
                    plan = {'items': [], 'value_delta': 0.0,
                            'bonus_earnable': self._can_meet_signup_requirement(card)}
                    if not plan['bonus_earnable']:
                        signup_bonus_value = 0
                    elif signup_bonus_value > 0:
                        months_needed = self._bonus_months_needed(card)
                        if months_needed > 0:
                            requirement = float((card.metadata.get('signup_bonus')
                                                 or {}).get('spending_requirement') or 0)
                            plan['items'].append(self._info_item(
                                'Bonus timeline',
                                f"${requirement:,.0f} requirement ÷ "
                                f"${self._total_monthly_spending():,.0f}/mo total "
                                f"spending ≈ {months_needed:.1f} months of your "
                                f"spending devoted to this bonus"))
                else:
                    plan = self._signup_bonus_plan(
                        card, portfolio_allocation,
                        rewards_breakdown['total_spending_on_card'])
                    if not plan['bonus_earnable']:
                        signup_bonus_value = 0
                    elif signup_bonus_value > 0:
                        months_needed = self._bonus_months_needed(card)
                        if months_needed > 0:
                            requirement = float((card.metadata.get('signup_bonus')
                                                 or {}).get('spending_requirement') or 0)
                            plan['items'].append(self._info_item(
                                'Bonus timeline',
                                f"${requirement:,.0f} requirement ÷ "
                                f"${self._total_monthly_spending():,.0f}/mo total "
                                f"spending ≈ {months_needed:.1f} months of your "
                                f"spending devoted to this bonus"))
                annual_rewards += plan['value_delta']
                rewards_breakdown['breakdown'].extend(plan['items'])

                estimated_value = annual_rewards - effective_fee + signup_bonus_value
                first_year_value = estimated_value

                fee_text = "first-year fee waived" if annual_fee_waived else f"${effective_fee:.0f} fee"
                if signup_bonus_value > 0:
                    shift_text = ""
                    if plan['value_delta']:
                        shift_text = (f", {'+' if plan['value_delta'] > 0 else '-'}"
                                      f"${abs(plan['value_delta']):.0f} from shifting spending "
                                      f"to meet the bonus requirement")
                    reasoning = (f"Total estimated value: ${estimated_value:.0f} "
                                 f"(${rewards_breakdown['total_rewards']:.0f} annual rewards - {fee_text} "
                                 f"+ ${signup_bonus_value:.0f} signup bonus{shift_text})")
                elif not plan['bonus_earnable']:
                    if bonus_deferred:
                        why = "doesn't fit this year's bonus capacity at your spending level"
                    else:
                        why = eligibility_note or 'spending requirement unreachable'
                    reasoning = (f"Total estimated value: ${estimated_value:.0f} "
                                 f"(${annual_rewards:.0f} annual rewards - {fee_text}; "
                                 f"signup bonus not counted — {why})")
                else:
                    reasoning = (f"Total estimated value: ${estimated_value:.0f} "
                                 f"(${annual_rewards:.0f} annual rewards - {fee_text})")
            else:
                signup_bonus_value = 0
                estimated_value = annual_rewards - annual_fee
                first_year_value = estimated_value
                ongoing_value = estimated_value
                verb = 'Keep' if action == 'keep' else 'Cancel'
                reasoning = (f"{verb} - ${annual_rewards:.0f} annual rewards vs "
                             f"${annual_fee:.0f} fee (net ${estimated_value:.0f})")

            line_total = sum(item['category_rewards'] for item in rewards_breakdown['breakdown'])
            fee_in_headline = effective_fee if action == 'apply' else annual_fee
            expected = line_total + signup_bonus_value - fee_in_headline
            if abs(estimated_value - expected) >= 1.0:
                logger.error(
                    f"Breakdown mismatch for {card.name} ({action}): headline "
                    f"${estimated_value:.2f} vs line items ${expected:.2f}")

            annual_fee_float = float(card.annual_fee)
            if action == 'cancel':
                card_credits_val, _ = cancel_credit_allocation.get(card.id, (0.0, []))
            elif card_action.get('duplicate_copy'):
                card_credits_val = 0.0
            else:
                card_credits_val, _ = credit_allocation.get(card.id, (0.0, []))

            pays_for_itself = (annual_fee_float > 0) and (card_credits_val >= annual_fee_float)

            rec = {
                'card': card,
                'action': action,
                'estimated_rewards': Decimal(str(estimated_value)),
                'first_year_value': first_year_value,
                'ongoing_value': ongoing_value,
                'reward_value_multiplier': multiplier,
                'valuation_note': f"Points/miles valued at {multiplier * 100:.2f}¢ each" if multiplier != 1 else "",
                'reasoning': reasoning,
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0),
                'signup_bonus_value': signup_bonus_value,
                'eligibility_note': eligibility_note,
                'bonus_deferred': bonus_deferred,
                'pays_for_itself': pays_for_itself,
                'priority': card_action.get('priority', 1)
            }
            if action == 'apply' and len(self.entities) > 1:
                apply_entity = self._eligible_entity_for_card(card) or self._primary_entity
                rec['apply_as'] = {
                    'entity_id': apply_entity.id,
                    'name': apply_entity.name,
                    'kind': apply_entity.kind,
                }
            recommendations.append(rec)

        return recommendations

    @staticmethod
    def _info_item(name, text):
        """A $0 informational breakdown line — never affects reconciliation."""
        return {
            'category_name': name, 'monthly_spend': 0, 'annual_spend': 0,
            'reward_rate': 0, 'reward_multiplier': 0, 'points_earned': 0,
            'category_rewards': 0, 'calculation': text, 'type': 'info',
        }

    def _total_monthly_spending(self) -> float:
        return self.rewards_calculator.total_monthly_spending()

    def _own_multiplier(self, card: CreditCard) -> float:
        return self.rewards_calculator.own_multiplier(card)

    def _program_multipliers(self, portfolio_cards: List[CreditCard]) -> dict:
        return self.rewards_calculator.program_multipliers(portfolio_cards)

    def _program_best_cards(self, portfolio_cards: List[CreditCard]) -> dict:
        return self.rewards_calculator.program_best_cards(portfolio_cards)

    def _effective_multiplier(self, card: CreditCard, program_multipliers: dict = None) -> float:
        return self.rewards_calculator.effective_multiplier(card, program_multipliers)

    def _bonus_months_needed(self, card: CreditCard) -> float:
        """Months of the user's TOTAL spending it takes to meet this card's signup requirement."""
        return self.bonus_capacity_manager.bonus_months_needed(card)

    def _bonus_capacity_plan(self, cards: List[CreditCard],
                             program_multipliers: dict = None) -> dict:
        """Single capacity authority: which of these cards' signup bonuses fit within BONUS_CAPACITY_MONTHS."""
        return self.bonus_capacity_manager.bonus_capacity_plan(cards, program_multipliers)

    def _signup_bonus_plan(self, card: CreditCard, portfolio_allocation: list,
                           allocated_annual_spend: float) -> dict:
        """Model how this card's signup spending requirement actually gets met."""
        return self.bonus_capacity_manager.signup_bonus_plan(
            card, portfolio_allocation, allocated_annual_spend)

    def _find_optimal_portfolio(self, current_cards: List[CreditCard], available_cards: List[CreditCard], max_cards: int) -> List[dict]:
        """Find the optimal combination of cards for maximum portfolio value."""
        return self.optimizer.find_optimal_portfolio(current_cards, available_cards, max_cards)

    def _evaluate_portfolio_scenario(self, cards_to_keep: List[CreditCard], cards_to_apply: List[CreditCard],
                                   available_cards: List[CreditCard], max_total_cards: int) -> dict:
        """Evaluate a specific portfolio scenario and return optimized actions."""
        return self.optimizer.evaluate_portfolio_scenario(
            cards_to_keep, cards_to_apply, available_cards, max_total_cards)

    def _select_optimal_card_combination(self, all_cards: List[CreditCard], max_cards: int) -> dict:
        """Select optimal combination of cards from all available."""
        return self.optimizer.select_optimal_card_combination(all_cards, max_cards)

    def _optimize_card_portfolio(self, card_scores: List[dict], max_cards: int) -> List[dict]:
        """Use portfolio optimization to select best card combination avoiding double counting."""
        return self.optimizer.optimize_card_portfolio(card_scores, max_cards)

    def _generate_card_reasoning(self, card_data: dict) -> str:
        """Generate reasoning text for a card recommendation."""
        return self.optimizer.generate_card_reasoning(card_data)

    def _select_best_new_cards(self, available_cards: List[CreditCard], max_new_cards: int) -> List[dict]:
        """Select best new cards to apply for."""
        return self.optimizer.select_best_new_cards(available_cards, max_new_cards)

    def _calculate_scenario_portfolio_value(self, actions: List[dict]) -> float:
        """Calculate net portfolio value for a scenario using fast portfolio optimization."""
        return self.optimizer.calculate_scenario_portfolio_value(actions)

    def _calculate_smart_card_value(self, card: CreditCard, signup_bonus: bool = True) -> float:
        """Calculate card value considering actual user spending and category competition."""
        return self.optimizer.calculate_smart_card_value(card, signup_bonus)

    def _calculate_spending_efficiency(self, card: CreditCard) -> float:
        """Calculate how efficiently a card matches user's actual spending pattern."""
        return self.optimizer.calculate_spending_efficiency(card)

    def _build_parent_category_spending(self) -> dict:
        """Build parent category spending map."""
        return self.rewards_calculator.build_parent_category_spending()

    def _eligible_entity_for_card(self, card: CreditCard):
        """Which household entity (if any) could apply for `card`."""
        return self.eligibility_manager.eligible_entity_for_card(card)

    def _holding_entity_for_card(self, card: CreditCard):
        """Which entity currently holds an OPEN copy of `card`, or None."""
        return self.eligibility_manager.holding_entity_for_card(card)

    def _is_eligible_for_card(self, card: CreditCard) -> bool:
        """Application eligibility: can ANY household entity get approved?"""
        return self.eligibility_manager.is_eligible_for_card(card)

    def _bonus_ineligibility_note(self, card: CreditCard):
        """User-facing reason this card's signup bonus is valued at $0."""
        return self.eligibility_manager.bonus_ineligibility_note(card)

    def _calculate_card_annual_rewards(self, card: CreditCard) -> float:
        """Calculate annual rewards for a card based on user spending."""
        return self.rewards_calculator.calculate_card_annual_rewards(card)

    def _calculate_portfolio_allocation(self, portfolio_cards: List[CreditCard]) -> list:
        """Allocate the user's annual spending across the portfolio."""
        return self.rewards_calculator.calculate_portfolio_allocation(portfolio_cards)

    def _calculate_card_allocated_breakdown(self, card: CreditCard, portfolio_allocation: list,
                                            credit_allocation: dict,
                                            program_multipliers: dict = None) -> dict:
        """Breakdown for one card using only the spending allocated to it."""
        return self.rewards_calculator.calculate_card_allocated_breakdown(
            card, portfolio_allocation, credit_allocation, program_multipliers)

    def _calculate_card_rewards_breakdown(self, card: CreditCard) -> dict:
        """Calculate detailed rewards breakdown for a card."""
        return self.rewards_calculator.calculate_card_rewards_breakdown(card)

    def _can_meet_signup_requirement(self, card: CreditCard) -> bool:
        """Check if user's total spending can meet the card's signup bonus requirement."""
        return self.bonus_capacity_manager.can_meet_signup_requirement(card)

    def _get_best_signup_bonus_card(self, eligible_cards: List[CreditCard]) -> dict:
        """Get the best signup bonus card as a fallback recommendation."""
        return self.bonus_capacity_manager.get_best_signup_bonus_card(eligible_cards)

    def _get_signup_bonus_value(self, card: CreditCard,
                                program_multipliers: dict = None) -> float:
        """Get signup bonus value using card's specific reward value multiplier."""
        return self.bonus_capacity_manager.get_signup_bonus_value(card, program_multipliers)

    def _recommend_for_expense(self, amount: float, category_slug: str, roadmap: Roadmap) -> dict:
        """One-off upcoming-expense recommendation (Phase N) — a parallel
        path to the portfolio roadmap, not a replacement. See
        `ExpenseRecommender` for the valuation shape."""
        eligible_cards = self._get_filtered_cards(roadmap)
        return self.expense_recommender.recommend_for_expense(
            amount, category_slug, eligible_cards, max_results=roadmap.max_recommendations)

    def _counted_card_credits(self, card: CreditCard) -> list:
        """Credits on this card that count for THIS user."""
        return self.credits_calculator.counted_card_credits(card)

    def _calculate_card_credits_value(self, card: CreditCard) -> tuple[float, list]:
        """Single-card credit value with NO portfolio context."""
        return self.credits_calculator.calculate_card_credits_value(card)

    @staticmethod
    def _credit_breakdown_item(credit: dict) -> dict:
        """Breakdown line for a counted credit."""
        from roadmaps.engine.calculators.credits import CreditsCalculator
        return CreditsCalculator.credit_breakdown_item(credit)


    def _allocate_portfolio_credits(self, cards: List[CreditCard]) -> dict:
        """Portfolio-wide credit allocation."""
        return self.credits_calculator.allocate_portfolio_credits(cards)

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
                'category_allocation': [],
                'card_count': 0
            }
        
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
                else:
                    cards_to_apply.append(card_data)
        
        all_portfolio_cards = cards_to_keep + cards_to_apply
        
        total_annual_fees = 0
        for card_data in all_portfolio_cards:
            card = card_data['card']
            if card_data['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                total_annual_fees += 0
            else:
                total_annual_fees += float(card.annual_fee)
        
        portfolio_cards = [card_data['card'] for card_data in all_portfolio_cards]
        portfolio_allocation = self._calculate_portfolio_allocation(portfolio_cards)
        
        total_portfolio_rewards = 0
        category_optimization = {}
        category_allocation = []

        logger.debug(f"self.spending_amounts in portfolio summary: {dict(self.spending_amounts)}")
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            logger.debug(f"{category_slug}: ${monthly_amount}/month -> ${annual_spend}/year")

        for entry in portfolio_allocation:
            card = entry['card']
            if card is None:
                category_allocation.append({
                    'category_slug': entry['category_slug'],
                    'category_name': entry['category_name'],
                    'card_id': None,
                    'card_name': None,
                    'rate': 0.0,
                    'annual_spend': entry['annual_spend'],
                    'annual_rewards': 0.0,
                    'is_base_rate': False,
                    'uncovered': True,
                })
                continue
            rate = entry['rate']
            annual_spend = entry['annual_spend']

            reward_value_multiplier = self._own_multiplier(card)
            category_rewards = annual_spend * rate * reward_value_multiplier
            total_portfolio_rewards += category_rewards

            category_allocation.append({
                'category_slug': entry['category_slug'],
                'category_name': entry['category_name'],
                'card_id': card.id,
                'card_name': card.name,
                'rate': rate,
                'annual_spend': annual_spend,
                'annual_rewards': category_rewards,
                'is_base_rate': entry['is_base_rate'],
                'uncovered': False,
            })

            if rate > 1.0:
                existing = category_optimization.get(entry['category_slug'])
                if existing is None or rate > existing['best_rate']:
                    category_optimization[entry['category_slug']] = {
                        'category_name': entry['category_name'],
                        'best_rate': rate,
                        'best_card': card.name,
                        'best_card_id': card.id,
                        'annual_spend': annual_spend,
                        'annual_rewards': category_rewards,
                        'max_annual_spend': entry['max_spend']
                    }

        total_parent_spending = sum(entry['annual_spend'] for entry in portfolio_allocation)
        
        credit_allocation = self._allocate_portfolio_credits(portfolio_cards)
        total_credits_value = sum(value for value, _ in credit_allocation.values())

        total_annual_rewards = total_portfolio_rewards + total_credits_value

        total_signup_bonuses = 0
        for card_data in all_portfolio_cards:
            if card_data['action'] == 'apply':
                signup_bonus = self._get_signup_bonus_value(card_data['card'])
                total_signup_bonuses += signup_bonus

        total_portfolio_rewards = total_annual_rewards + total_signup_bonuses
        logger.debug(f"Portfolio Summary - signup bonuses: ${total_signup_bonuses:.2f}")

        net_portfolio_value = total_portfolio_rewards - total_annual_fees

        if net_portfolio_value < 0:
            logger.warning(f"Portfolio optimization resulted in negative value: ${net_portfolio_value:.2f}")
            logger.debug(f"Total rewards: ${total_portfolio_rewards:.2f}, Total fees: ${total_annual_fees:.2f}")
            logger.debug(f"Portfolio cards: {len(all_portfolio_cards)}")

        result = {
            'total_annual_fees': total_annual_fees,
            'total_portfolio_rewards': total_portfolio_rewards,
            'total_annual_rewards': total_annual_rewards,
            'net_portfolio_value': net_portfolio_value,
            'category_optimization': category_optimization,
            'category_allocation': category_allocation,
            'card_count': len(all_portfolio_cards),
            'total_credits_value': total_credits_value,
            'total_annual_spending': total_parent_spending,
            'category_optimization_cards': {cat_data['best_card'] for cat_data in category_optimization.values()}
        }
        return result

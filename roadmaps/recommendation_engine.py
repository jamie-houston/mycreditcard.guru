import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from cards.models import CreditCard, UserSpendingProfile, UserCard
from .models import Roadmap

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Core recommendation engine that considers:
    - User spending patterns
    - Issuer policies (5/24 rule, etc.)
    - Reward optimization
    - Annual fee vs. benefits analysis
    """
    
    # A year of bonus-earning capacity: counted signup bonuses consume
    # months of the user's total spending (see _bonus_months_needed).
    BONUS_CAPACITY_MONTHS = 12.0

    def __init__(self, profile: UserSpendingProfile, user_cards_data=None, strategy=None):
        from .strategies import strategy_weights
        self.profile = profile
        # Strategy weights shape SELECTION only (which cards make the
        # portfolio); displayed dollar values stay honest so every headline
        # still reconciles to its line items.
        self.strategy = strategy
        self.weights = strategy_weights(strategy)
        # All reward-category lookups are filtered to what's active today so
        # expired rotating quarters never count.
        self.today = date.today()
        # Get user cards from the user, not the profile. `user_cards` is the
        # OPEN cards (they earn rewards); `card_history` includes closed
        # cards too — eligibility rules like Chase 5/24 and Amex's lifetime
        # bonus rule look at everything the user has ever held.
        if profile.user:
            self.card_history = list(
                profile.user.owned_cards.select_related('card__issuer').all())
            self.user_cards = [uc for uc in self.card_history
                               if uc.closed_date is None]
        else:
            self.card_history = []
            self.user_cards = []

        # For session-based users, accept user cards data directly
        if user_cards_data and not profile.user:
            from django.utils.dateparse import parse_date
            from cards.models import CreditCard
            # Convert user cards data to mock UserCard objects for consistency
            mock_user_cards = []
            for card_data in user_cards_data:
                try:
                    card = CreditCard.objects.get(id=card_data['card_id'])
                    # Create a mock object with the same interface as UserCard
                    mock_card = type('MockUserCard', (), {
                        'card': card,
                        'opened_date': parse_date(card_data.get('opened_date', '2020-01-01')),
                        'closed_date': None if card_data.get('is_active', True) else parse_date(card_data.get('opened_date', '2020-01-01')),
                        'nickname': card_data.get('nickname', ''),
                        'bonus_earned_date': parse_date(card_data['bonus_earned_date']) if card_data.get('bonus_earned_date') else None,
                        'bonus_override': card_data.get('bonus_override'),
                    })()
                    mock_user_cards.append(mock_card)
                except CreditCard.DoesNotExist:
                    continue
            self.card_history = mock_user_cards
            self.user_cards = [uc for uc in mock_user_cards
                               if uc.closed_date is None]
        
        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount
            for sa in profile.spending_amounts.all()
        }
        # Per-instance credit caches — selection loops value the same cards
        # over and over, so counted credits are computed once per card.
        self._card_credits_cache = {}
        self._credit_prefs = None
        self._credit_spending_categories = None


    def generate_quick_recommendations(self, roadmap: Roadmap) -> List[dict]:
        """Generate recommendations without saving to database (includes breakdowns)"""
        # Reload spending amounts to ensure we have the latest data
        self.spending_amounts = {
            sa.category.slug: sa.monthly_amount
            for sa in self.profile.spending_amounts.all()
        }
        # Spending changed ⇒ category-credit matching may change too.
        self._card_credits_cache = {}
        self._credit_prefs = None
        self._credit_spending_categories = None
        logger.debug(f"Reloaded spending_amounts: {dict(self.spending_amounts)}")
        
        # Get all eligible cards based on filters
        eligible_cards = self._get_filtered_cards(roadmap)
        
        # Generate portfolio-optimized recommendations
        recommendations = self._generate_portfolio_optimized_recommendations(eligible_cards, roadmap)
        
        # Fallback: If no apply recommendations and high spending, force at least one
        apply_recommendations = [rec for rec in recommendations if rec['action'] == 'apply']
        total_annual_spending = sum(float(amount) * 12 for amount in self.spending_amounts.values())
        
        if not apply_recommendations and total_annual_spending > 30000:  # $30k+ annual spending
            logger.debug(f"High spending (${total_annual_spending:.0f}/year) with no apply recommendations - adding fallback")
            fallback_rec = self._get_best_signup_bonus_card(eligible_cards)
            if fallback_rec:
                recommendations.append(fallback_rec)
                logger.debug(f"Added fallback recommendation: APPLY {fallback_rec['card'].name}")
        
        # DEBUG: Print recommendations before filtering
        logger.debug(f"Generated {len(recommendations)} recommendations before filtering:")
        for rec in recommendations:
            logger.debug(f"  - {rec['action'].upper()}: {rec['card'].name} (priority: {rec['priority']})")
        
        # Separate recommendations by action type for smart filtering
        keeps_and_applies = [rec for rec in recommendations if rec['action'] in ['keep', 'apply', 'upgrade', 'downgrade']]
        cancels = [rec for rec in recommendations if rec['action'] == 'cancel']
        
        # Separate $0 fee keeps (always show) from other keeps/applies
        zero_fee_keeps = [rec for rec in keeps_and_applies if rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0]
        other_keeps_applies = [rec for rec in keeps_and_applies if not (rec['action'] == 'keep' and float(rec['card'].annual_fee) == 0)]
        
        # Separate applies from other keeps for balanced filtering
        applies = [rec for rec in other_keeps_applies if rec['action'] == 'apply']
        other_keeps = [rec for rec in other_keeps_applies if rec['action'] != 'apply']
        
        # Sort by priority (lower number = higher priority)
        applies.sort(key=lambda x: x['priority'])
        other_keeps.sort(key=lambda x: x['priority'])
        
        # Separate current card actions (keeps/cancels) from new card actions (applies)
        # Note: Some keeps might get converted to cancels in the validation step, so we include both
        current_card_actions = [rec for rec in other_keeps if rec['action'] in ['keep']] + cancels
        new_card_actions = applies
        
        # ALWAYS include ALL current card recommendations (keeps and cancels)
        # Users need to see what happens to each of their existing cards
        filtered_other_keeps_applies = current_card_actions.copy()
        
        # max_recommendations should apply only to NEW card applications
        # Current cards (keeps/cancels) must always be shown regardless of max_recommendations
        max_new_card_applications = roadmap.max_recommendations

        # Include best apply recommendations up to max_new_card_applications,
        # AND within the year's bonus-earning capacity: each counted signup
        # bonus consumes months of the user's total spending
        # (_bonus_months_needed), and there are only 12 in a year. A $2K/mo
        # spender can't work three $10K requirements this year — the third
        # card is deferred, not shown. Keeping windows sequential also keeps
        # each card's bonus_shift line items honest (they'd double-count the
        # same dollars if windows overlapped).
        months_committed = 0.0
        deferred_applies = []
        timeline = []
        bonus_less_applies = []
        if new_card_actions:
            # An apply worth $0 or less is noise — never tell someone to
            # open a card that earns them nothing. (Selection-time
            # efficiency boosts can drag these in; the displayed value is
            # the honest one, so filter on it.)
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
                    # Selection (_bonus_capacity_plan, via the valuation
                    # sites) already zeroes signup_bonus_value for bonuses
                    # that don't fit, so nothing with a positive bonus
                    # should legitimately land here anymore — this loop is
                    # now just a safety net. A positive bonus arriving here
                    # means selection and this priority-ordered assembly
                    # disagreed on what fits (e.g. differing sort order);
                    # it's still deferred, but log it as unexpected.
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

            # Sequencing: recompute the capacity plan over the FINAL apply
            # set so each apply's month offset reflects exactly what's
            # being shown, not the possibly-larger candidate set Step 2 saw.
            # Shrinking the set can only free up budget, never take it away
            # (removing entries can't increase any prefix's committed
            # total), so a bonus counted here was already counted upstream.
            sequence_plan = self._bonus_capacity_plan(
                [rec['card'] for rec in selected_applies])
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
                    # No bonus budget consumed — "apply whenever" (a later
                    # Companion-Pass-era phase may push these to chase next
                    # year's bonus instead).
                    rec['recommended_month'] = 0
                    rec['bonus_months_needed'] = 0.0
                    if rec.get('bonus_deferred') and entry and entry['counted']:
                        # Self-heals on regenerate: the smaller final apply
                        # set freed enough budget that this bonus would now
                        # fit, but Step 2 already froze the display at $0
                        # for this round (see Phase E risk notes).
                        logger.warning(
                            f"{rec['card'].name} shows bonus_deferred but the "
                            f"final sequence plan counts its bonus — will "
                            f"self-heal on the next regeneration.")
                elif entry and entry['counted']:
                    rec['recommended_month'] = int(round(entry['start_month']))
                    rec['bonus_months_needed'] = round(entry['months'], 1)
                else:
                    # Shouldn't happen — a positive-bonus apply that
                    # survived assembly but the recomputed plan says its
                    # bonus doesn't fit. Treat like bonus-less rather than
                    # crash; log for investigation.
                    logger.warning(
                        f"{rec['card'].name} has signup_bonus_value="
                        f"${float(rec.get('signup_bonus_value', 0)):.0f} but the final "
                        f"sequence plan doesn't count it — selection/display divergence.")
                    rec['recommended_month'] = 0
                    rec['bonus_months_needed'] = round(entry['months'], 1) if entry else 0.0

            # Timeline: applies ascending by actual start_month, bonus-less
            # last (they have no window to place on the timeline).
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

        # Non-apply recs carry no sequencing fields.
        for rec in recommendations:
            if rec['action'] != 'apply':
                rec['recommended_month'] = None
                rec['bonus_months_needed'] = None
        
        # VALIDATION: Convert negative-value keeps to cancels
        for rec in recommendations:
            if rec['action'] == 'keep':
                estimated_value = float(rec['estimated_rewards'])
                annual_fee = float(rec['card'].annual_fee)
                
                # Never recommend "keep" for cards with negative value (unless $0 fee)
                if estimated_value < 0 and annual_fee > 0:
                    rec['action'] = 'cancel'
                    rec['reasoning'] = f"Cancel - losing money: ${estimated_value + annual_fee:.0f} rewards vs ${annual_fee:.0f} fee (net: ${estimated_value:.0f})"
        
        # DEBUG: Print smart filtering details
        logger.debug(f"Smart filtering breakdown:")
        logger.debug(f"  - Other keeps/applies: {len(filtered_other_keeps_applies)}")
        logger.debug(f"  - Zero fee keeps: {len(zero_fee_keeps)}")
        # Recount cancels after validation
        actual_cancels = [rec for rec in recommendations if rec['action'] == 'cancel']
        logger.debug(f"  - Cancels: {len(actual_cancels)}")
        logger.debug(f"Final {len(recommendations)} recommendations after smart filtering:")
        for rec in recommendations:
            fee_info = f" (${rec['card'].annual_fee} fee)" if rec['action'] in ['keep', 'cancel'] else ""
            logger.debug(f"  - {rec['action'].upper()}: {rec['card'].name}{fee_info} (priority: {rec['priority']})")
        
        # Calculate portfolio summary for the recommended cards
        portfolio_summary = self._calculate_portfolio_summary(recommendations)

        # Bonus-capacity summary: how much of the year's spending the
        # recommended bonuses consume, and which applies didn't fit.
        portfolio_summary['bonus_capacity'] = {
            'total_monthly_spending': self._total_monthly_spending(),
            'months_committed': round(months_committed, 1),
            'capacity_months': self.BONUS_CAPACITY_MONTHS,
            'deferred_applies': [rec['card'].name for rec in deferred_applies],
            'timeline': timeline,
            'bonus_less_applies': bonus_less_applies,
        }
        
        # NOTE: breakdowns are intentionally never stripped — every card's
        # headline value must stay reproducible from its visible line items.
        # (Allocation already keeps non-optimal cards' breakdowns small.)
        for rec in recommendations:
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
        """Apply roadmap filters to get eligible cards.

        Multiple filters of the SAME type OR together (e.g. reward_type
        Points + Miles = either); different types AND. Chaining .filter()
        per filter would AND everything and same-type pairs would match
        nothing."""
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
                    # Expect format like "0" or "0-95" or "95+"
                    if '+' in value:
                        type_q |= Q(annual_fee__gte=Decimal(value.replace('+', '')))
                    elif '-' in value:
                        min_fee, max_fee = map(Decimal, value.split('-'))
                        type_q |= Q(annual_fee__gte=min_fee, annual_fee__lte=max_fee)
                    else:
                        type_q |= Q(annual_fee=Decimal(value))
            queryset = queryset.filter(type_q)
        
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
        logger.debug(f"User has {len(current_cards)} current cards:")
        for card in current_cards:
            logger.debug(f"  - {card.name}")
        logger.debug(f"Found {len(available_new_cards)} available new cards")
        logger.debug(f"Max recommendations allowed: {roadmap.max_recommendations}")
        logger.debug(f"Will scenario 1 use optimization? {len(current_cards) == 0}")
        logger.debug(f"Will scenario 2 use optimization? {True}")
        
        # Generate all possible portfolio combinations and evaluate them
        # max_cards should be current cards + max new recommendations, not just max_recommendations
        max_total_cards = len(current_cards) + roadmap.max_recommendations
        best_portfolio = self._find_optimal_portfolio(current_cards, available_new_cards, max_total_cards)

        # De-dup: scenario assembly can emit the same card twice (e.g. a
        # keep from optimization plus a cancel appended separately).
        # Keep/apply wins over cancel; otherwise first occurrence wins.
        actions_by_card = {}
        for card_action in best_portfolio:
            card_id = card_action['card'].id
            existing = actions_by_card.get(card_id)
            if existing is None or (existing['action'] == 'cancel'
                                    and card_action['action'] in ('keep', 'apply')):
                actions_by_card[card_id] = card_action
        best_portfolio = list(actions_by_card.values())

        # Spending allocation spans only cards the user will actually hold;
        # a card recommended for cancellation can't earn category rewards.
        held_cards = [ca['card'] for ca in best_portfolio if ca['action'] in ('keep', 'apply')]
        portfolio_allocation = self._calculate_portfolio_allocation(held_cards)
        credit_allocation = self._allocate_portfolio_credits(held_cards)

        # Bonus capacity, computed once over the final apply set so display
        # agrees with selection: a bonus that didn't fit the 12-month budget
        # shows $0 here too (see _bonus_capacity_plan). Stashed for Step 3's
        # sequencing, which reuses this same computation.
        apply_cards = [ca['card'] for ca in best_portfolio if ca['action'] == 'apply']
        capacity_plan = self._bonus_capacity_plan(apply_cards)
        self._last_capacity_plan = capacity_plan

        # Convert optimal portfolio to recommendations
        for card_action in best_portfolio:
            card = card_action['card']
            action = card_action['action']

            # Individual card values come from its allocated spending, so
            # every headline number reconciles with its line items.
            if action == 'cancel':
                # Counterfactual: what keeping this card would net, with
                # spending optimally re-allocated across held cards + it.
                # Shows the honest cost of keeping rather than the bare fee.
                cancel_allocation = self._calculate_portfolio_allocation(held_cards + [card])
                cancel_credit_allocation = self._allocate_portfolio_credits(held_cards + [card])
                rewards_breakdown = self._calculate_card_allocated_breakdown(
                    card, cancel_allocation, cancel_credit_allocation)
            else:
                rewards_breakdown = self._calculate_card_allocated_breakdown(
                    card, portfolio_allocation, credit_allocation)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            multiplier = rewards_breakdown['reward_multiplier']

            eligibility_note = ''
            bonus_deferred = False
            if action == 'apply':
                signup_bonus_value = self._get_signup_bonus_value(card)
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else annual_fee
                # Ongoing value reflects steady state — no bonus, no
                # bonus-window spending shifts.
                ongoing_value = annual_rewards - annual_fee

                bonus_block = self._bonus_ineligibility_note(card)
                capacity_entry = capacity_plan['by_card_id'].get(card.id)
                if bonus_block:
                    # Issuer bonus rules zero the bonus for THIS user; no
                    # point modeling shift spending for a bonus that won't
                    # pay. The card competes on ongoing value alone.
                    eligibility_note = bonus_block
                    signup_bonus_value = 0
                    plan = {'items': [self._info_item(
                        'Signup bonus not counted', bonus_block)],
                        'value_delta': 0.0, 'bonus_earnable': False}
                elif (capacity_entry is not None and not capacity_entry['counted']
                      and signup_bonus_value > 0):
                    # Bonus is earnable but doesn't fit this year's 12-month
                    # spending budget (selection already scored it this way —
                    # see _bonus_capacity_plan). No bonus_shift items: we're
                    # not chasing a bonus we're not counting, so the
                    # reconciliation guard holds by construction.
                    bonus_deferred = True
                    signup_bonus_value = 0
                    plan = {'items': [self._info_item(
                        'Signup bonus deferred',
                        "Doesn't fit this year's bonus capacity at your "
                        "spending level — card recommended on ongoing value; "
                        "earn the bonus next year")],
                        'value_delta': 0.0, 'bonus_earnable': False}
                else:
                    plan = self._signup_bonus_plan(
                        card, portfolio_allocation,
                        rewards_breakdown['total_spending_on_card'])
                    if not plan['bonus_earnable']:
                        signup_bonus_value = 0
                    elif signup_bonus_value > 0:
                        # Bonus timeline: how many months of the user's
                        # total spending this requirement consumes (feeds
                        # the yearly bonus-capacity cap in assembly).
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
            else:  # keep or cancel
                signup_bonus_value = 0
                estimated_value = annual_rewards - annual_fee
                first_year_value = estimated_value
                ongoing_value = estimated_value
                verb = 'Keep' if action == 'keep' else 'Cancel'
                reasoning = (f"{verb} - ${annual_rewards:.0f} annual rewards vs "
                             f"${annual_fee:.0f} fee (net ${estimated_value:.0f})")

            # Reconciliation guard: the headline must equal the sum of the
            # line items plus signup bonus minus the fee. By construction it
            # does; if this ever fires, the math above regressed.
            line_total = sum(item['category_rewards'] for item in rewards_breakdown['breakdown'])
            fee_in_headline = effective_fee if action == 'apply' else annual_fee
            expected = line_total + signup_bonus_value - fee_in_headline
            if abs(estimated_value - expected) >= 1.0:
                logger.error(
                    f"Breakdown mismatch for {card.name} ({action}): headline "
                    f"${estimated_value:.2f} vs line items ${expected:.2f}")

            recommendations.append({
                'card': card,
                'action': action,
                'estimated_rewards': Decimal(str(estimated_value)),  # Show true value, including negative for cancel cards
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
                'priority': card_action.get('priority', 1)
            })

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
        return sum(float(amount) for amount in self.spending_amounts.values())

    def _bonus_months_needed(self, card: CreditCard) -> float:
        """Months of the user's TOTAL spending it takes to meet this card's
        signup requirement — the scarce resource behind bonus sequencing.
        $2K/mo spend against a $10K requirement = 5 months in which every
        dollar runs through this card. 0 when there's no requirement;
        inf when the user spends nothing."""
        signup_bonus = card.metadata.get('signup_bonus') or {}
        requirement = float(signup_bonus.get('spending_requirement') or 0)
        if requirement <= 0:
            return 0.0
        monthly = self._total_monthly_spending()
        if monthly <= 0:
            return float('inf')
        return requirement / monthly

    def _bonus_capacity_plan(self, cards: List[CreditCard]) -> dict:
        """Single capacity authority: which of these cards' signup bonuses
        fit within BONUS_CAPACITY_MONTHS of the user's spending this year.

        Reuses _get_signup_bonus_value and _bonus_months_needed — no second
        source of truth. Bonuses with no spending requirement (months == 0)
        are free: always counted, consume no budget. Bonuses with a
        requirement are sorted by value density (bonus_value / months,
        descending) — the right greedy heuristic for "budget of months,
        maximize counted bonus dollars" — with a total-order tie-break
        (bonus_value desc, then card.id) so equal-density fixtures can't
        flap. All-or-nothing per bonus: walk the budget in that order, each
        bonus either fits (counted, consuming months starting where the
        previous counted bonus left off) or doesn't (uncounted). A bonus
        needing infinite months (zero total spending) always falls out
        uncounted.

        Computed from the SET of candidate cards, not greedy add order, so
        the same portfolio always yields the same counted/uncounted split
        — and the walk order doubles as the sequencing order.

        Returns:
            by_card_id: {card.id: {'bonus_value', 'months', 'counted',
                         'start_month'}} ('start_month' is None when
                         uncounted)
            months_committed: sum of counted bonuses' months
            sequence: counted card ids in spend-consumption order
        """
        entries = [{
            'card': card,
            'bonus_value': self._get_signup_bonus_value(card),
            'months': self._bonus_months_needed(card),
        } for card in cards]

        free = sorted((e for e in entries if e['months'] == 0),
                      key=lambda e: e['card'].id)
        metered = sorted(
            (e for e in entries if e['months'] > 0),
            key=lambda e: (-(e['bonus_value'] / e['months']),
                           -e['bonus_value'], e['card'].id))

        by_card_id = {}
        sequence = []
        for e in free:
            by_card_id[e['card'].id] = {
                'bonus_value': e['bonus_value'], 'months': 0.0,
                'counted': True, 'start_month': 0.0,
            }
            sequence.append(e['card'].id)

        committed = 0.0
        for e in metered:
            months = e['months']
            if months != float('inf') and committed + months <= self.BONUS_CAPACITY_MONTHS:
                by_card_id[e['card'].id] = {
                    'bonus_value': e['bonus_value'], 'months': months,
                    'counted': True, 'start_month': committed,
                }
                sequence.append(e['card'].id)
                committed += months
            else:
                by_card_id[e['card'].id] = {
                    'bonus_value': e['bonus_value'], 'months': months,
                    'counted': False, 'start_month': None,
                }

        return {
            'by_card_id': by_card_id,
            'months_committed': committed,
            'sequence': sequence,
        }

    def _signup_bonus_plan(self, card: CreditCard, portfolio_allocation: list,
                           allocated_annual_spend: float) -> dict:
        """Model how this card's signup spending requirement actually gets met.

        Three outcomes:
        - Organic: the card's own allocated spending covers the requirement
          within the window — informational item only, no cost.
        - Shift: spending allocated to other cards must temporarily move to
          this card during the bonus window. It earns this card's base rate
          but foregoes the incumbent card's (usually better) rate; each
          shift is a line item whose net value is the honest cost of
          chasing the bonus. Cheapest spending shifts first.
        - Unreachable: even shifting every dollar the user spends can't
          meet the requirement — the bonus is worth $0 and says so.

        Returns {'items': [line items], 'value_delta': float,
                 'bonus_earnable': bool}.
        """
        signup_bonus = card.metadata.get('signup_bonus') or {}
        requirement = float(signup_bonus.get('spending_requirement') or 0)
        months = float(signup_bonus.get('time_limit_months') or 3)
        if requirement <= 0:
            return {'items': [], 'value_delta': 0.0, 'bonus_earnable': True}

        window = months / 12
        organic = allocated_annual_spend * window

        info_item = self._info_item

        if organic >= requirement:
            return {
                'items': [info_item(
                    'Signup bonus requirement',
                    f"${requirement:,.0f} in {months:.0f} months — covered by "
                    f"~${organic:,.0f} you'd already spend on this card")],
                'value_delta': 0.0,
                'bonus_earnable': True,
            }

        # Spending must shift from other cards. This card earns its base
        # rate on shifted spend (anything it rated higher already won that
        # category in the allocation).
        this_mult = float(card.metadata.get('reward_value_multiplier', 0.01))
        this_rate = 1.0
        for rc in card.reward_categories.active_on(self.today).select_related('category'):
            if rc.category.slug in self.BASE_CATEGORY_SLUGS:
                this_rate = max(this_rate, float(rc.reward_rate))
        this_value = this_rate * this_mult

        sources = []
        for entry in portfolio_allocation:
            if entry['annual_spend'] <= 0:
                continue
            if entry['card'] is not None and entry['card'].id == card.id:
                continue
            if entry['card'] is None:
                other_value = 0.0
            else:
                other_mult = float(entry['card'].metadata.get('reward_value_multiplier', 0.01))
                other_value = entry['rate'] * other_mult
            sources.append((other_value - this_value, other_value, entry))
        sources.sort(key=lambda s: s[0])  # cheapest opportunity cost first

        shortfall = requirement - organic
        items = []
        value_delta = 0.0
        for cost_per_dollar, other_value, entry in sources:
            if shortfall <= 0:
                break
            available = entry['annual_spend'] * window
            take = min(shortfall, available)
            if take <= 0:
                continue
            earn = take * this_value
            forgo = take * other_value
            net = earn - forgo
            value_delta += net
            if entry['card'] is None:
                detail = (f"${take:,.0f} of unrewarded spending moved here for "
                          f"{months:.0f} mo: earns {this_rate:.1f}x (${earn:.2f})")
                name = f"Bonus window: {entry['category_name']} (uncovered)"
            else:
                detail = (f"${take:,.0f} moved here for {months:.0f} mo: earns "
                          f"{this_rate:.1f}x (${earn:.2f}) instead of "
                          f"{entry['rate']:.1f}x on {entry['card'].name} "
                          f"(${forgo:.2f}) = ${net:+.2f}")
                name = f"Bonus window: {entry['category_name']} from {entry['card'].name}"
            items.append({
                'category_name': name,
                'monthly_spend': take / months,
                'annual_spend': take,
                'reward_rate': this_rate,
                'reward_multiplier': this_mult,
                'points_earned': take * this_rate,
                'category_rewards': net,
                'calculation': detail,
                'type': 'bonus_shift',
            })
            shortfall -= take

        if shortfall > 0:
            # Even every dollar of the user's spending can't reach the
            # requirement — the bonus is not real money for this user.
            return {
                'items': [info_item(
                    'Signup bonus unreachable',
                    f"Needs ${requirement:,.0f} in {months:.0f} months but your "
                    f"total spending in that window is "
                    f"~${requirement - shortfall:,.0f} — bonus valued at $0")],
                'value_delta': 0.0,
                'bonus_earnable': False,
            }

        items.insert(0, info_item(
            'Signup bonus requirement',
            f"${requirement:,.0f} in {months:.0f} months — "
            f"~${organic:,.0f} from spending allocated to this card, "
            f"${requirement - organic:,.0f} shifted from other cards (below)"))
        return {'items': items, 'value_delta': value_delta, 'bonus_earnable': True}
    
    def _find_optimal_portfolio(self, current_cards: List[CreditCard], available_cards: List[CreditCard], max_cards: int) -> List[dict]:
        """Find the optimal combination of cards for maximum portfolio value"""
        # Start with current cards and evaluate what to do with each
        portfolio_actions = []
        
        # Evaluate portfolio scenarios
        scenarios = []
        
        # Scenario 1: Evaluate current cards individually, keep profitable ones, add best new cards
        profitable_current_cards = []
        unprofitable_current_cards = []
        for card in current_cards:
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            net_value = annual_rewards - annual_fee
            
            # Keep profitable cards or zero-fee cards
            if net_value >= 0 or annual_fee == 0:
                profitable_current_cards.append(card)
            else:
                unprofitable_current_cards.append((card, annual_rewards, annual_fee))
        
        scenario1 = self._evaluate_portfolio_scenario(
            cards_to_keep=profitable_current_cards,
            cards_to_apply=[],
            available_cards=available_cards,
            max_total_cards=max_cards
        )
        
        # Add cancel actions for unprofitable cards to scenario1
        for card, annual_rewards, annual_fee in unprofitable_current_cards:
            scenario1['actions'].append({
                'card': card,
                'action': 'cancel',
                'reasoning': f"Cancel - losing money: ${annual_rewards:.0f} rewards vs ${annual_fee} fee (net: ${annual_rewards - annual_fee:.0f})",
                'priority': 1
            })
        
        scenarios.append(("keep_profitable_add_new", scenario1))
        
        # Scenario 2: Optimize current cards (may cancel some), add best new cards
        scenario2 = self._evaluate_portfolio_scenario(
            cards_to_keep=[],  # Will evaluate each current card
            cards_to_apply=current_cards + available_cards,  # All cards considered equally
            available_cards=[],
            max_total_cards=max_cards
        )
        scenarios.append(("full_optimization", scenario2))
        
        # DEBUG: Print scenario comparison
        logger.debug(f"Scenario comparison:")
        for name, scenario in scenarios:
            actions_summary = {}
            for action in scenario['actions']:
                action_type = action['action']
                actions_summary[action_type] = actions_summary.get(action_type, 0) + 1
            logger.debug(f"  {name}: value=${scenario['net_portfolio_value']:.2f}, actions={actions_summary}")
        
        # Choose best scenario
        best_scenario = max(scenarios, key=lambda x: x[1]['net_portfolio_value'])
        logger.debug(f"Selected scenario: {best_scenario[0]} with value ${best_scenario[1]['net_portfolio_value']:.2f}")
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
                    logger.debug(f"Scenario 1 using portfolio optimization for {len(available_cards)} available cards")
                    return self._select_optimal_card_combination(available_cards, max_total_cards)
                else:
                    # ALWAYS use full optimization to consider dropping current cards for better new ones
                    logger.debug(f"Scenario 2 using FULL portfolio optimization with {len(cards_to_keep)} current + {len(available_cards)} new cards")
                    all_cards = list(cards_to_keep) + available_cards
                    full_optimization = self._select_optimal_card_combination(all_cards, max_total_cards)
                    
                    # Compare with keep-all scenario
                    best_new_cards = self._select_best_new_cards(available_cards, remaining_slots)
                    actions.extend(best_new_cards)
                    keep_all_value = self._calculate_scenario_portfolio_value(actions)
                    
                    # Use full optimization if it's better
                    if full_optimization and full_optimization['net_portfolio_value'] > keep_all_value:
                        logger.debug(f"Full optimization better: ${full_optimization['net_portfolio_value']:.2f} vs ${keep_all_value:.2f}")
                        return full_optimization
                    else:
                        logger.debug(f"Keep-all scenario better: ${keep_all_value:.2f} vs ${full_optimization.get('net_portfolio_value', 0):.2f}")
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
                # Pre-sort scoring keeps the full bonus — capacity is
                # portfolio-relative and a solo card has the whole budget —
                # except a defensive cap: a bonus that can't fit even alone
                # shouldn't rank the card as if it will. The real,
                # portfolio-relative capacity decision happens in the
                # valuation sites below (_bonus_capacity_plan).
                if self._bonus_months_needed(card) > self.BONUS_CAPACITY_MONTHS:
                    signup_bonus_value = 0
                annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
                effective_fee = 0 if annual_fee_waived else float(card.annual_fee)
                base_net_value = annual_rewards - effective_fee + signup_bonus_value
                action = 'apply'
            
            # Strategy weights: selection-time value, never displayed.
            scored_value = (base_net_value
                            + signup_bonus_value * (self.weights['signup_bonus_weight'] - 1)
                            - self.weights['per_card_penalty'])

            # Apply efficiency scoring: boost cards that are highly relevant to user's spending
            efficiency_score = self._calculate_spending_efficiency(card)
            if efficiency_score > 0.8:  # Super boost for highly relevant cards
                efficiency_boost = scored_value * efficiency_score * 2.0  # Up to 200% boost for perfect efficiency
            else:
                efficiency_boost = scored_value * efficiency_score * 1.0  # Up to 100% boost for normal cards
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
        
        # Allocation spans only the cards the user would hold (the optimal
        # set) — cards being cancelled can't claim category spending.
        portfolio_allocation = self._calculate_portfolio_allocation(
            [cd['card'] for cd in optimal_cards])
        credit_allocation = self._allocate_portfolio_credits(
            [cd['card'] for cd in optimal_cards])

        for uc in self.user_cards:
            if uc.card.id not in optimal_card_ids:
                annual_fee = float(uc.card.annual_fee)

                # Use allocated breakdown for consistent values
                rewards_breakdown = self._calculate_card_allocated_breakdown(
                    uc.card, portfolio_allocation, credit_allocation)
                annual_rewards = rewards_breakdown['total_rewards']
                
                # Skip cancellation recommendations for $0 annual fee cards
                if annual_fee == 0:
                    # Instead, add as a "keep" recommendation with low priority
                    logger.debug(f"Keeping $0 fee card instead of canceling: {uc.card.name}")
                    actions.append({
                        'card': uc.card,
                        'action': 'keep',
                        'reasoning': f"Keep - no annual fee card (${annual_rewards:.0f} rewards, $0 fee)",
                        'priority': 60  # Lower priority than optimal keeps
                    })
                else:
                    # Only recommend canceling cards with annual fees
                    logger.debug(f"Recommending cancel for fee card: {uc.card.name} (${annual_fee} fee)")
                    actions.append({
                        'card': uc.card,
                        'action': 'cancel',
                        'reasoning': f"Cancel - provides no additional portfolio value (${annual_rewards:.0f} rewards vs ${annual_fee:.0f} fee)",
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
            for reward_cat in card.reward_categories.active_on(self.today):
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

            # Capacity-aware bonus counting, same authority as
            # _calculate_scenario_portfolio_value (see _bonus_capacity_plan)
            # — this combination's applies may not be the same set the
            # caller ultimately picks, so it's recomputed per combination.
            apply_cards_in_combination = [cd['card'] for cd in card_combination
                                          if cd['action'] == 'apply']
            combination_capacity_plan = self._bonus_capacity_plan(apply_cards_in_combination)

            # Calculate credits/benefits value for each card
            for card_data in card_combination:
                card = card_data['card']

                # Add annual fee
                if card_data['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                    # First year fee waived
                    pass
                else:
                    total_fees += float(card.annual_fee)

                # Add signup bonus for new cards (strategy-weighted: this
                # function only ranks combinations, it never reaches the UI)
                # — only if it's counted within this combination's capacity.
                if card_data['action'] == 'apply':
                    entry = combination_capacity_plan['by_card_id'].get(card.id)
                    if entry and entry['counted']:
                        total_value += entry['bonus_value'] * self.weights['signup_bonus_weight']

                # Track best reward rate per category across all cards
                for reward_cat in card.reward_categories.active_on(self.today):
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

            # Credits use the portfolio allocation so a second copy of a
            # non-stackable credit can't win selection on phantom value it
            # would never display.
            credit_allocation = self._allocate_portfolio_credits(
                [cd['card'] for cd in card_combination])
            total_value += sum(value for value, _ in credit_allocation.values())

            # Strategy effort cost: every held card must earn its keep
            card_count_cost = self.weights['per_card_penalty'] * len(card_combination)
            return total_value - total_fees - card_count_cost
        
                 # Try different combinations to find optimal portfolio
        best_combination = []
        best_value = 0  # Start with $0 - only accept positive portfolio values!
        
        # Always include current cards (keeps) - let portfolio optimization decide profitability
        must_include = [cd for cd in card_scores if cd['action'] == 'keep']
        remaining_cards = [cd for cd in card_scores if cd not in must_include]
        
        logger.debug(f"Portfolio optimization - must_include: {len(must_include)}, remaining: {len(remaining_cards)}, max_cards: {max_cards}")
        
        # Start with empty portfolio (value = $0) as baseline
        empty_portfolio_value = calculate_portfolio_value([])
        if empty_portfolio_value > best_value:
            best_value = empty_portfolio_value
            best_combination = []
            logger.debug(f"Empty portfolio baseline - value: ${best_value:.2f}")
        
        # Aggressive performance optimization - limit search space dramatically
        max_combinations = min(len(remaining_cards), max_cards - len(must_include))
        
        # Sort remaining cards by individual net value for smarter search
        remaining_cards.sort(key=lambda x: x['net_value'], reverse=True)
        
        # DEBUG: Show top cards being considered with efficiency scores
        logger.debug(f"Top 15 cards by net value (with efficiency scoring):")
        for i, card_data in enumerate(remaining_cards[:15]):
            base_val = card_data.get('base_net_value', card_data['net_value'])
            efficiency = card_data.get('efficiency_score', 0)
            boost = card_data.get('efficiency_boost', 0)
            logger.debug(f"  {i+1}. {card_data['card'].name}: ${card_data['net_value']:.0f} (base: ${base_val:.0f}, efficiency: {efficiency:.2f}, boost: +${boost:.0f})")
        
        # DEBUG: Specifically look for Amazon Prime card
        amazon_cards = [cd for cd in remaining_cards if 'Amazon' in cd['card'].name]
        if amazon_cards:
            logger.debug(f"Amazon cards with efficiency:")
            for i, card_data in enumerate(amazon_cards):
                base_val = card_data.get('base_net_value', card_data['net_value'])
                efficiency = card_data.get('efficiency_score', 0)
                boost = card_data.get('efficiency_boost', 0)
                logger.debug(f"  Amazon {i+1}. {card_data['card'].name}: ${card_data['net_value']:.0f} (base: ${base_val:.0f}, efficiency: {efficiency:.2f}, boost: +${boost:.0f})")
        else:
            logger.debug(f"No Amazon cards found in remaining_cards")
        
        # Only test top cards to limit exponential explosion
        cards_to_test = remaining_cards[:min(20, len(remaining_cards))]  # Top 20 cards to include relevant niche cards
        logger.debug(f"Testing top {len(cards_to_test)} cards for performance")
        
        # Use greedy approach: add cards one by one in order of individual value
        # This ensures consistent results regardless of max_cards
        current_combination = must_include.copy()
        current_value = calculate_portfolio_value(current_combination) if current_combination else 0
        
        if current_value > best_value:
            best_value = current_value
            best_combination = current_combination.copy()
            logger.debug(f"Base combination - value: ${best_value:.2f}, cards: {[cd['card'].name for cd in best_combination]}")
        
        # Add cards one by one, always picking the one that adds most value
        available_cards = cards_to_test.copy()
        
        while len(current_combination) < max_cards and available_cards:
            best_addition = None
            best_addition_value = current_value
            
            # Test each remaining card to see which adds most value
            for card_to_add in available_cards:
                test_combination = current_combination + [card_to_add]
                test_actions = [{'card': cd['card'], 'action': cd['action']} for cd in test_combination]
                test_value = self._calculate_scenario_portfolio_value(test_actions)
                
                if test_value > best_addition_value:
                    best_addition_value = test_value
                    best_addition = card_to_add
            
            # If we found a beneficial addition, add it
            if best_addition and best_addition_value > current_value:
                current_combination.append(best_addition)
                available_cards.remove(best_addition)
                current_value = best_addition_value
                
                if current_value > best_value:
                    best_value = current_value
                    best_combination = current_combination.copy()
                    logger.debug(f"Added {best_addition['card'].name} - value: ${best_value:.2f}, cards: {[cd['card'].name for cd in best_combination]}")
            else:
                # No beneficial additions found, stop
                break
        
        # If no positive portfolio found, return empty (no recommendations)
        if best_value <= 0:
            logger.debug(f"No profitable portfolio found - returning no recommendations")
            return []
        
        # Ensure we don't return more than max_cards
        return best_combination[:max_cards]
    
    def _generate_card_reasoning(self, card_data: dict) -> str:
        """Generate reasoning text for a card recommendation"""
        card = card_data['card']
        action = card_data['action']
        
        if action == 'apply':
            # Calculate the actual estimated value that user will see
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus = self._get_signup_bonus_value(card)
            annual_fee_waived = card.metadata.get('annual_fee_waived_first_year', False)
            effective_fee = 0 if annual_fee_waived else float(card.annual_fee)
            total_estimated_value = annual_rewards - effective_fee + signup_bonus
            
            fee_text = " (first year fee waived)" if annual_fee_waived else f" (${card.annual_fee} annual fee)"
            if signup_bonus > 0:
                return f"Total estimated value: ${total_estimated_value:.0f} (${annual_rewards:.0f} annual rewards - ${effective_fee} fee + ${signup_bonus:.0f} signup bonus)"
            else:
                return f"Total estimated value: ${total_estimated_value:.0f} (${annual_rewards:.0f} annual rewards - ${effective_fee} fee)"
        elif action == 'keep':
            # Calculate actual value for keep actions too
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            net_value = annual_rewards - annual_fee
            return f"Keep - earning ${annual_rewards:.0f} annually vs ${annual_fee} fee (net: ${net_value:.0f})"
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
                    'rewards_breakdown': rewards_breakdown['breakdown'],
                    'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0)
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

        # Capacity-aware: only bonuses that fit this year's 12-month budget
        # count toward the scenario's value — an over-budget bonus can't
        # inflate a portfolio's ranking, only its ongoing value can win it
        # a slot (see _bonus_capacity_plan).
        apply_cards_in_scenario = [action['card'] for action in portfolio_cards
                                   if action['action'] == 'apply']
        capacity_plan = self._bonus_capacity_plan(apply_cards_in_scenario)

        for action in portfolio_cards:
            card = action['card']
            if action['action'] == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
                total_annual_fees += 0  # First year waived
            else:
                total_annual_fees += float(card.annual_fee)

            # Add signup bonus for new cards (strategy-weighted: scenario
            # values only rank portfolios, they're never displayed) — only
            # if it's counted within this scenario's bonus capacity.
            if action['action'] == 'apply':
                entry = capacity_plan['by_card_id'].get(card.id)
                if entry and entry['counted']:
                    total_signup_bonuses += (entry['bonus_value']
                                             * self.weights['signup_bonus_weight'])

        # Credits the user actually redeems count toward selection —
        # without this, a credit-heavy card loses the greedy race even
        # though its displayed value (which includes credits) wins.
        # Portfolio-allocated: duplicate non-stackable credits count once.
        credit_allocation = self._allocate_portfolio_credits(
            [action['card'] for action in portfolio_cards])
        total_credits_value = sum(value for value, _ in credit_allocation.values())

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
                card._cached_reward_categories = list(card.reward_categories.active_on(self.today).select_related('category'))
            
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
        
        base_portfolio_value = (total_portfolio_rewards + total_credits_value
                                + total_signup_bonuses - total_annual_fees)
        
        # Add efficiency bonus: boost portfolios that include highly relevant cards
        total_efficiency_boost = 0
        for action in portfolio_cards:
            card = action['card']
            efficiency_score = self._calculate_spending_efficiency(card)
            
            if efficiency_score > 0.1:  # Boost any somewhat relevant cards (lowered threshold)
                card_annual_value = self._calculate_smart_card_value(card, signup_bonus=False) - float(card.annual_fee)
                # Capacity-aware, same as the bonus sum above: an
                # over-budget bonus must not inflate value through the
                # efficiency boost either, or it partially defeats
                # bonus-less competition (see _bonus_capacity_plan).
                if action['action'] == 'apply':
                    entry = capacity_plan['by_card_id'].get(card.id)
                    card_signup_value = ((entry['bonus_value'] * self.weights['signup_bonus_weight'])
                                         if entry and entry['counted'] else 0)
                else:
                    card_signup_value = 0
                card_base_value = card_annual_value + card_signup_value
                efficiency_boost = card_base_value * efficiency_score * 0.5  # 50% max boost for perfect efficiency
                total_efficiency_boost += efficiency_boost

        # Strategy effort cost: every held card must earn its keep
        card_count_cost = self.weights['per_card_penalty'] * len(portfolio_cards)
        final_value = base_portfolio_value + total_efficiency_boost - card_count_cost

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
        parent_categories_with_subcategories = set()
        
        # First pass: identify parent categories that have subcategories with spending
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory and annual_spend > 0:
                    parent_categories_with_subcategories.add(spending_category.parent.slug)
            except SpendingCategory.DoesNotExist:
                pass
        
        # Second pass: calculate parent category spending correctly  
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    # This is a subcategory, add its spending to the parent
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    # This is a parent category
                    if category_slug in parent_categories_with_subcategories:
                        # Parent has subcategories with spending, so don't double count
                        # The subcategories will be aggregated in the first part of this loop
                        pass
                    else:
                        # Parent category with no subcategory spending, include its direct spending
                        parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                # Category doesn't exist in database, treat as parent category
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
            card._cached_reward_categories = list(card.reward_categories.active_on(self.today).select_related('category'))
        
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
            card._cached_reward_categories = list(card.reward_categories.active_on(self.today).select_related('category'))
        
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
                    'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0),
                    'reasoning': f"Total estimated value: ${total_estimated_value:.0f} (${annual_rewards:.0f} annual rewards - ${effective_annual_fee} fee{' - first year fee waived' if annual_fee_waived_first_year else ''} + ${signup_bonus_value:.0f} signup bonus)"
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
                'total_spending_on_card': card_data.get('total_spending_on_card', 0),
                'signup_bonus_value': card_data['signup_bonus'],
                'priority': i + 1
            })
        
        return recommendations
    
    def _is_eligible_for_card(self, card: CreditCard) -> bool:
        """Application eligibility: can the user get approved at all?

        Data-driven issuer rules (Chase 5/24, BofA 2/3/4, Capital One
        1-per-6-months, family blocks) live in roadmaps/eligibility.py and
        are evaluated against the full card history, closed cards included.
        Blocked cards are silently skipped — the roadmap picks the
        next-best card instead.
        """
        from .eligibility import application_block

        # Already holds this exact card (open) — can't apply again.
        if any(uc.card.id == card.id for uc in self.user_cards):
            return False

        return application_block(card, self.card_history, self.today) is None

    def _bonus_ineligibility_note(self, card: CreditCard):
        """User-facing reason this card's signup bonus is valued at $0
        (Amex lifetime, Citi 48-month, Sapphire/Southwest rules...), or
        None when the bonus looks earnable. Cached per card — it's called
        from every scoring site via _get_signup_bonus_value."""
        if not hasattr(self, '_bonus_notes'):
            self._bonus_notes = {}
        if card.id not in self._bonus_notes:
            from .eligibility import bonus_ineligibility
            self._bonus_notes[card.id] = bonus_ineligibility(
                card, self.card_history, self.today)
        return self._bonus_notes[card.id]
    
    def _calculate_card_annual_rewards(self, card: CreditCard) -> float:
        """Calculate annual rewards for a card based on user spending"""
        breakdown = self._calculate_card_rewards_breakdown(card)
        return breakdown['total_rewards']
    
    BASE_CATEGORY_SLUGS = ('general', 'other', 'everything-else')

    def _calculate_portfolio_allocation(self, portfolio_cards: List[CreditCard]) -> list:
        """Allocate the user's annual spending across the portfolio.

        Each spending category the user entered is walked from the
        best-rate eligible card downward; spending beyond a reward
        category's annual cap rolls over to the next-best card, ending
        at the best flat/base-rate card. The sum of allocated spending
        always equals the user's total annual spending — entries with
        card=None mark spending no portfolio card covers, so totals
        still reconcile.

        Returns a list of allocation entries:
            {category_slug, category_name, card, rate, annual_spend,
             max_spend, reward_category_id, is_base_rate}
        """
        from cards.models import SpendingCategory

        # De-dup cards: scoring paths can hand us the same card twice.
        seen_ids = set()
        cards = []
        for card in portfolio_cards:
            if card.id not in seen_ids:
                seen_ids.add(card.id)
                cards.append(card)

        # Collect each card's active reward categories once.
        category_rewards = []  # (card, reward_cat) for specific categories
        base_rewards = []      # (card, reward_cat) for base/catch-all rates
        for card in cards:
            active = card.reward_categories.active_on(self.today).select_related(
                'category', 'category__parent')
            for reward_cat in active:
                if reward_cat.category.slug in self.BASE_CATEGORY_SLUGS:
                    base_rewards.append((card, reward_cat))
                else:
                    category_rewards.append((card, reward_cat))

        # Cap room is shared per reward-category row: two spending slugs
        # that hit the same capped 5x bucket draw from one allowance.
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

        for spending_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            if annual_spend <= 0:
                continue

            parent_slug = None
            try:
                spend_category = SpendingCategory.objects.select_related('parent').get(
                    slug=spending_slug)
                category_name = spend_category.display_name or spend_category.name
                if spend_category.parent:
                    parent_slug = spend_category.parent.slug
            except SpendingCategory.DoesNotExist:
                category_name = spending_slug.replace('_', ' ').title()

            # A card matches this spending if it rates the category itself
            # or the category's parent (a parent-level rate covers leaf
            # spending). Base rates compete too — a 2% everything card
            # should beat a 1.5% category rate.
            matches = [
                (card, reward_cat) for card, reward_cat in category_rewards
                if reward_cat.category.slug == spending_slug
                or (parent_slug and reward_cat.category.slug == parent_slug)
            ]
            candidates = sorted(matches + base_rewards,
                                key=lambda cr: float(cr[1].reward_rate), reverse=True)
            allocate(spending_slug, category_name, annual_spend, candidates)

        return allocation

    def _calculate_card_allocated_breakdown(self, card: CreditCard, portfolio_allocation: list,
                                            credit_allocation: dict) -> dict:
        """Breakdown for one card using only the spending allocated to it by
        _calculate_portfolio_allocation and the credits attributed to it by
        _allocate_portfolio_credits (computed over the same card set)."""
        total_rewards = 0.0
        breakdown_details = []
        reward_value_multiplier = float(card.metadata.get('reward_value_multiplier', 0.01))

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

        # Credits come from the portfolio-wide allocation, so a non-stackable
        # credit duplicated across cards counts once (the other carriers get
        # $0 info lines, never invisible subtraction).
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
        parent_categories_with_subcategories = set()
        
        # First pass: identify parent categories that have subcategories with spending
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory and annual_spend > 0:
                    parent_categories_with_subcategories.add(spending_category.parent.slug)
            except SpendingCategory.DoesNotExist:
                pass
        
        # Second pass: calculate parent category spending correctly
        for category_slug, annual_spend in all_spending.items():
            try:
                spending_category = SpendingCategory.objects.get(slug=category_slug)
                if spending_category.is_subcategory:
                    # This is a subcategory, add its spending to the parent
                    parent_slug = spending_category.parent.slug
                    parent_category_spending[parent_slug] = parent_category_spending.get(parent_slug, 0.0) + annual_spend
                else:
                    # This is a parent category
                    if category_slug in parent_categories_with_subcategories:
                        # Parent has subcategories with spending, so don't double count
                        # The subcategories will be aggregated in the first part of this loop
                        pass
                    else:
                        # Parent category with no subcategory spending, include its direct spending
                        parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
            except SpendingCategory.DoesNotExist:
                # Category doesn't exist in database, treat as parent category
                parent_category_spending[category_slug] = parent_category_spending.get(category_slug, 0.0) + annual_spend
        
        # Track which spending has been allocated to specific reward categories
        allocated_spending = 0.0
        
        # Calculate rewards for specific reward categories
        for reward_category in card.reward_categories.active_on(self.today):
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
                
                # Add to breakdown with clearer display
                category_display_name = reward_category.category.display_name or reward_category.category.name
                # Format category name with multiplier like "Travel (4x)"
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
                
                # Format other spending with multiplier
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
        
        # Add card credits to the total rewards if user has selected them
        # (single-card scoring path — no portfolio context, no dedup)
        credits_value, credits_breakdown = self._calculate_card_credits_value(card)
        total_rewards += credits_value
        for credit in credits_breakdown:
            breakdown_details.append(self._credit_breakdown_item(credit))

        # Calculate total spending on this card
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
    
    def _can_meet_signup_requirement(self, card: CreditCard) -> bool:
        """Check if user's total spending can meet the card's signup bonus
        requirement. Prefers the structured metadata over parsing the
        human-readable requirement string."""
        signup_bonus = card.metadata.get('signup_bonus') or {}
        required_amount = float(signup_bonus.get('spending_requirement') or 0)
        time_months = float(signup_bonus.get('time_limit_months') or 0)

        if not required_amount:
            # Fall back to parsing a requirement string like "$5000 in 3 months"
            if not card.signup_bonus_requirement:
                return True
            import re
            match = re.search(r'\$([\d,]+).*?(\d+)\s*months?', card.signup_bonus_requirement)
            if not match:
                return True  # If we can't parse, assume achievable
            required_amount = float(match.group(1).replace(',', ''))
            time_months = float(match.group(2))

        if required_amount <= 0:
            return True
        if time_months <= 0:
            time_months = 3  # most common bonus window

        total_monthly_spending = sum(float(amount) for amount in self.spending_amounts.values())
        user_spending_in_period = total_monthly_spending * time_months

        # Add 20% buffer for achievability (user might increase spending slightly)
        return user_spending_in_period * 1.2 >= required_amount

    def _get_best_signup_bonus_card(self, eligible_cards: List[CreditCard]) -> dict:
        """Get the best signup bonus card as a fallback recommendation for high spenders"""
        # Filter to only new cards (not currently owned). Works for session
        # users too — self.user_cards covers both real and mock cards.
        # Issuer application rules apply here too: a 5/24-blocked card must
        # not sneak back in through the high-spender fallback.
        owned_card_ids = {uc.card.id for uc in self.user_cards}
        new_cards = [card for card in eligible_cards
                     if card.id not in owned_card_ids
                     and self._is_eligible_for_card(card)]
        
        best_card = None
        best_value = 0
        
        for card in new_cards:
            signup_bonus = self._get_signup_bonus_value(card)
            annual_fee = float(card.annual_fee)
            
            # Simple net value: signup bonus minus first year fee
            net_value = signup_bonus - annual_fee
            
            if net_value > best_value:
                best_value = net_value
                best_card = card
        
        if best_card:
            # Breakdown uses allocated spending across current cards plus
            # this candidate, so its value doesn't double-count categories
            # the user's existing cards already win.
            current_cards = [uc.card for uc in self.user_cards]
            allocation = self._calculate_portfolio_allocation(current_cards + [best_card])
            credit_allocation = self._allocate_portfolio_credits(current_cards + [best_card])
            rewards_breakdown = self._calculate_card_allocated_breakdown(
                best_card, allocation, credit_allocation)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus = self._get_signup_bonus_value(best_card)
            annual_fee = float(best_card.annual_fee)
            
            # Calculate net estimated value same as main logic
            annual_fee_waived = best_card.metadata.get('annual_fee_waived_first_year', False)
            effective_fee = 0 if annual_fee_waived else annual_fee
            estimated_rewards = annual_rewards - effective_fee + signup_bonus
            
            return {
                'card': best_card,
                'action': 'apply',
                'estimated_rewards': estimated_rewards,
                'reasoning': f"High spending fallback - ${signup_bonus:.0f} signup bonus",
                'priority': 15,  # Medium priority - better than low keeps but after optimal applies
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0),
                'signup_bonus_value': signup_bonus
            }
        
        return None

    def _get_signup_bonus_value(self, card: CreditCard) -> float:
        """Get signup bonus value using card's specific reward value multiplier.

        Returns $0 when issuer bonus rules make the bonus unearnable for
        THIS user (see _bonus_ineligibility_note) — the card still competes
        on ongoing value, matching the unreachable-requirement pathway."""
        if self._bonus_ineligibility_note(card):
            return 0.0
        if card.signup_bonus_amount and self._can_meet_signup_requirement(card):
            # Check signup bonus type to determine if conversion is needed
            signup_bonus_type = getattr(card, 'signup_bonus_type', None)
            
            if signup_bonus_type and hasattr(signup_bonus_type, 'name'):
                bonus_type_name = signup_bonus_type.name.lower()
            elif signup_bonus_type:
                bonus_type_name = str(signup_bonus_type).lower()
            else:
                bonus_type_name = 'unknown'
            
            if bonus_type_name in ['cashback', 'cash', 'cash back']:
                # Cashback signup bonuses are already in dollars. No
                # sanity-check heuristics here: a wrong number means the
                # card's source data is wrong — fix the data, not the math.
                return float(card.signup_bonus_amount)
            else:
                # Points/miles need to be converted using reward value multiplier
                reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
                bonus_value = float(card.signup_bonus_amount) * float(reward_value_multiplier)
                return bonus_value
        return 0.0
    
    def _counted_card_credits(self, card: CreditCard) -> list:
        """Credits on this card that count for THIS user (preference-selected
        benefits + category credits matching real spending), cached per
        engine instance — selection loops value the same cards heavily.

        Each entry is a credit dict tagged with 'dedup_key' and 'stackable'
        for _allocate_portfolio_credits, the single dedup authority."""
        cached = self._card_credits_cache.get(card.id)
        if cached is not None:
            return cached

        if self._credit_prefs is None:
            prefs = set()
            if hasattr(self.profile, 'spending_credit_preferences'):
                prefs = set(
                    pref.spending_credit.slug
                    for pref in self.profile.spending_credit_preferences.filter(values_credit=True)
                )
            self._credit_prefs = prefs
            self._credit_spending_categories = set(
                spending.category.slug
                for spending in self.profile.spending_amounts.all()
                if spending.monthly_amount > 0
            )

        entries = []
        for card_credit in card.credits.filter(is_active=True).select_related(
                'spending_credit', 'category'):
            if card_credit.spending_credit and card_credit.spending_credit.slug in self._credit_prefs:
                credit_type = "benefit"
                credit_name = card_credit.spending_credit.display_name
                dedup_key = card_credit.spending_credit.slug
                stackable = card_credit.spending_credit.stackable
            elif card_credit.category and card_credit.category.slug in self._credit_spending_categories:
                credit_type = "category"
                credit_name = f"{card_credit.category.display_name} Credit"
                # Spend-offset statement credits: each card's credit offsets
                # separate spending, so duplicates always stack.
                dedup_key = f"category_{card_credit.category.slug}"
                stackable = True
            else:
                continue

            annual_value = float(card_credit.value) * card_credit.times_per_year
            frequency_text = ""
            if card_credit.times_per_year > 1:
                frequency_text = f" (${card_credit.value} × {card_credit.times_per_year}/year)"

            entries.append({
                'name': credit_name or card_credit.description,
                'value': float(card_credit.value),
                'times_per_year': card_credit.times_per_year,
                'annual_value': annual_value,
                'type': credit_type,
                'description': card_credit.description,
                'frequency_display': frequency_text,
                'dedup_key': dedup_key,
                'stackable': stackable,
            })

        self._card_credits_cache[card.id] = entries
        return entries

    def _calculate_card_credits_value(self, card: CreditCard) -> tuple[float, list]:
        """Single-card credit value with NO portfolio context — candidate
        scoring only. Anything displayed as an assembled portfolio must use
        _allocate_portfolio_credits instead."""
        entries = self._counted_card_credits(card)
        return sum(e['annual_value'] for e in entries), entries

    @staticmethod
    def _credit_breakdown_item(credit: dict) -> dict:
        """Breakdown line for a counted credit (same shape as reward lines)."""
        if credit['times_per_year'] > 1:
            credit_display = f"{credit['name']} (${credit['value']:.0f}×{credit['times_per_year']})"
        else:
            credit_display = f"{credit['name']} (${credit['value']:.0f})"
        return {
            'category_name': credit_display,
            'monthly_spend': 0,
            'annual_spend': 0,
            'reward_rate': 0,
            'reward_multiplier': 1.0,
            'points_earned': credit['annual_value'],
            'category_rewards': credit['annual_value'],
            'calculation': f"Card benefit: ${credit['annual_value']:.0f} annually",
            'type': 'credit',
            'credit_detail': credit,
        }

    def _allocate_portfolio_credits(self, cards: List[CreditCard]) -> dict:
        """Portfolio-wide credit allocation — the single dedup authority for
        selection, display, and summary.

        Stackable credits count on every card that carries them. A
        non-stackable one (lounge membership, streaming subscription — a
        second copy covers nothing) counts on exactly ONE card: the carrier
        where it's worth the most, ties to the lowest card id. Every other
        carrier gets a $0 info line naming the counted card, so each card's
        line items still sum to its headline and the reconciliation guard
        stays green by construction.

        Returns {card_id: (credits_value, credit_breakdown_items)} covering
        every card passed in."""
        values = {}
        items = {}
        non_stackable = {}  # dedup_key -> {card_id: {'card', 'entries', 'total'}}
        for card in cards:
            if card.id in values:
                continue
            values[card.id] = 0.0
            items[card.id] = []
            for entry in self._counted_card_credits(card):
                if entry['stackable']:
                    values[card.id] += entry['annual_value']
                    items[card.id].append(self._credit_breakdown_item(entry))
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
                        items[card_id].append(self._credit_breakdown_item(entry))
                else:
                    name = carrier['entries'][0]['name']
                    items[card_id].append(self._info_item(
                        f"{name} (counted once)",
                        f"{name} doesn't stack across cards — "
                        f"counted once, on {winner['card'].name}"))

        return {card_id: (values[card_id], items[card_id]) for card_id in values}
    
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
        
        # Use the corrected portfolio allocation method for consistent results
        portfolio_cards = [card_data['card'] for card_data in all_portfolio_cards]
        portfolio_allocation = self._calculate_portfolio_allocation(portfolio_cards)
        
        # Calculate total portfolio rewards from the allocation
        total_portfolio_rewards = 0
        category_optimization = {}
        
        logger.debug(f"self.spending_amounts in portfolio summary: {dict(self.spending_amounts)}")
        for category_slug, monthly_amount in self.spending_amounts.items():
            annual_spend = float(monthly_amount) * 12
            logger.debug(f"{category_slug}: ${monthly_amount}/month -> ${annual_spend}/year")
        
        # Build category optimization from portfolio allocation
        for entry in portfolio_allocation:
            card = entry['card']
            if card is None:
                continue  # spending no portfolio card covers earns nothing
            rate = entry['rate']
            annual_spend = entry['annual_spend']

            reward_value_multiplier = float(card.metadata.get('reward_value_multiplier', 0.01))
            category_rewards = annual_spend * rate * reward_value_multiplier
            total_portfolio_rewards += category_rewards

            # Category optimization display: primary (highest-rate) entry
            # per category, only when it beats the 1x floor
            if rate > 1.0:
                existing = category_optimization.get(entry['category_slug'])
                if existing is None or rate > existing['best_rate']:
                    category_optimization[entry['category_slug']] = {
                        'category_name': entry['category_name'],
                        'best_rate': rate,
                        'best_card': card.name,
                        'annual_spend': annual_spend,
                        'annual_rewards': category_rewards,
                        'max_annual_spend': entry['max_spend']
                    }

        # Calculate total annual spending for summary
        total_parent_spending = sum(entry['annual_spend'] for entry in portfolio_allocation)
        
        # Card credits from the same portfolio-wide allocation the per-card
        # breakdowns use, so the summary equals Σ line items by construction:
        # non-stackable duplicates count once, stackable/category duplicates
        # count on every card that carries them.
        credit_allocation = self._allocate_portfolio_credits(portfolio_cards)
        total_credits_value = sum(value for value, _ in credit_allocation.values())

        total_portfolio_rewards += total_credits_value
        
        # Add signup bonuses for new card applications
        total_signup_bonuses = 0
        for card_data in all_portfolio_cards:
            if card_data['action'] == 'apply':
                signup_bonus = self._get_signup_bonus_value(card_data['card'])
                total_signup_bonuses += signup_bonus
        
        total_portfolio_rewards += total_signup_bonuses
        logger.debug(f"Portfolio Summary - signup bonuses: ${total_signup_bonuses:.2f}")
        
        # Calculate net portfolio value (rewards - fees)
        net_portfolio_value = total_portfolio_rewards - total_annual_fees
        
        # ENSURE NET VALUE IS NEVER NEGATIVE by design
        # If negative, it means the optimization failed - this should not happen
        # with proper portfolio optimization, but let's log it for debugging
        if net_portfolio_value < 0:
            logger.warning(f"Portfolio optimization resulted in negative value: ${net_portfolio_value:.2f}")
            logger.debug(f"Total rewards: ${total_portfolio_rewards:.2f}, Total fees: ${total_annual_fees:.2f}")
            logger.debug(f"Portfolio cards: {len(all_portfolio_cards)}")
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
    

import logging
import re
from typing import List
from cards.models import CreditCard
from ..utils import info_item

logger = logging.getLogger(__name__)

class BonusCapacityManager:
    """
    Manages qualification rules, spend-consumption rates (months needed),
    signup bonus opportunity cost planning, and 12-month capacity scheduling.
    """

    def __init__(self, engine):
        self.engine = engine

    def bonus_months_needed(self, card: CreditCard) -> float:
        """Months of the user's TOTAL spending it takes to meet this card's signup requirement."""
        signup_bonus = card.metadata.get('signup_bonus') or {}
        requirement = float(signup_bonus.get('spending_requirement') or 0)
        if requirement <= 0:
            return 0.0
        monthly = self.engine._total_monthly_spending()
        if monthly <= 0:
            return float('inf')
        return requirement / monthly

    def bonus_capacity_plan(self, cards: List[CreditCard], program_multipliers: dict = None) -> dict:
        """Single capacity authority: which of these cards' signup bonuses fit within BONUS_CAPACITY_MONTHS."""
        entries = [{
            'card': card,
            'bonus_value': self.get_signup_bonus_value(card, program_multipliers),
            'months': self.bonus_months_needed(card),
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
            if months != float('inf') and committed + months <= self.engine.BONUS_CAPACITY_MONTHS:
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

    def signup_bonus_plan(self, card: CreditCard, portfolio_allocation: list,
                           allocated_annual_spend: float) -> dict:
        """Model how this card's signup spending requirement actually gets met."""
        signup_bonus = card.metadata.get('signup_bonus') or {}
        requirement = float(signup_bonus.get('spending_requirement') or 0)
        months = float(signup_bonus.get('time_limit_months') or 3)
        if requirement <= 0:
            return {'items': [], 'value_delta': 0.0, 'bonus_earnable': True}

        window = months / 12
        organic = allocated_annual_spend * window

        if organic >= requirement:
            return {
                'items': [info_item(
                    'Signup bonus requirement',
                    f"${requirement:,.0f} in {months:.0f} months — covered by "
                    f"~${organic:,.0f} you'd already spend on this card")],
                'value_delta': 0.0,
                'bonus_earnable': True,
            }

        this_mult = self.engine._own_multiplier(card)
        this_rate = 1.0
        for rc in card.reward_categories.active_on(self.engine.today).select_related('category'):
            if rc.category.slug in self.engine.rewards_calculator.BASE_CATEGORY_SLUGS:
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
                other_mult = self.engine._own_multiplier(entry['card'])
                other_value = entry['rate'] * other_mult
            sources.append((other_value - this_value, other_value, entry))
        sources.sort(key=lambda s: s[0])

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

    def can_meet_signup_requirement(self, card: CreditCard) -> bool:
        """Check if user's total spending can meet the card's signup bonus requirement."""
        signup_bonus = card.metadata.get('signup_bonus') or {}
        required_amount = float(signup_bonus.get('spending_requirement') or 0)
        time_months = float(signup_bonus.get('time_limit_months') or 0)

        if not required_amount:
            if not card.signup_bonus_requirement:
                return True
            match = re.search(r'\$([\d,]+).*?(\d+)\s*months?', card.signup_bonus_requirement)
            if not match:
                return True
            required_amount = float(match.group(1).replace(',', ''))
            time_months = float(match.group(2))

        if required_amount <= 0:
            return True
        if time_months <= 0:
            time_months = 3

        total_monthly_spending = sum(float(amount) for amount in self.engine.spending_amounts.values())
        user_spending_in_period = total_monthly_spending * time_months
        return user_spending_in_period * 1.2 >= required_amount

    def get_best_signup_bonus_card(self, eligible_cards: List[CreditCard]) -> dict:
        """Get the best signup bonus card as a fallback recommendation for high spenders."""
        owned_card_ids = {uc.card.id for uc in self.engine.user_cards}
        new_cards = [card for card in eligible_cards
                     if card.id not in owned_card_ids
                     and self.engine._is_eligible_for_card(card)]

        best_card = None
        best_value = 0

        for card in new_cards:
            signup_bonus = self.get_signup_bonus_value(card)
            annual_fee = float(card.annual_fee)
            net_value = signup_bonus - annual_fee

            if net_value > best_value:
                best_value = net_value
                best_card = card

        if best_card:
            current_cards = [uc.card for uc in self.engine.user_cards]
            allocation = self.engine._calculate_portfolio_allocation(current_cards + [best_card])
            credit_allocation = self.engine._allocate_portfolio_credits(current_cards + [best_card])
            fallback_program_multipliers = self.engine._program_multipliers(current_cards + [best_card])
            rewards_breakdown = self.engine._calculate_card_allocated_breakdown(
                best_card, allocation, credit_allocation, fallback_program_multipliers)
            annual_rewards = rewards_breakdown['total_rewards']
            signup_bonus = self.get_signup_bonus_value(best_card, fallback_program_multipliers)
            annual_fee = float(best_card.annual_fee)

            annual_fee_waived = best_card.metadata.get('annual_fee_waived_first_year', False)
            effective_fee = 0 if annual_fee_waived else annual_fee
            estimated_rewards = annual_rewards - effective_fee + signup_bonus

            fallback_rec = {
                'card': best_card,
                'action': 'apply',
                'estimated_rewards': estimated_rewards,
                'reasoning': f"High spending fallback - ${signup_bonus:.0f} signup bonus",
                'priority': 15,
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'total_spending_on_card': rewards_breakdown.get('total_spending_on_card', 0),
                'signup_bonus_value': signup_bonus
            }
            if len(self.engine.entities) > 1:
                apply_entity = self.engine._eligible_entity_for_card(best_card) or self.engine._primary_entity
                fallback_rec['apply_as'] = {
                    'entity_id': apply_entity.id,
                    'name': apply_entity.name,
                    'kind': apply_entity.kind,
                }
            return fallback_rec

        return None

    def get_signup_bonus_value(self, card: CreditCard, program_multipliers: dict = None) -> float:
        """Get signup bonus value using card's specific reward value multiplier."""
        if self.engine._bonus_ineligibility_note(card):
            return 0.0
        if card.signup_bonus_amount and self.can_meet_signup_requirement(card):
            signup_bonus_type = getattr(card, 'signup_bonus_type', None)

            if signup_bonus_type and hasattr(signup_bonus_type, 'name'):
                bonus_type_name = signup_bonus_type.name.lower()
            elif signup_bonus_type:
                bonus_type_name = str(signup_bonus_type).lower()
            else:
                bonus_type_name = 'unknown'

            if bonus_type_name in ['cashback', 'cash', 'cash back']:
                return float(card.signup_bonus_amount)
            else:
                reward_value_multiplier = self.engine._effective_multiplier(card, program_multipliers)
                bonus_value = float(card.signup_bonus_amount) * reward_value_multiplier
                return bonus_value
        return 0.0

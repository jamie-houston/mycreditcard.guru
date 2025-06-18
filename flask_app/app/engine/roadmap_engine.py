"""Credit card roadmap and portfolio management engine."""
import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
from app.models.user_card import UserCard
from app.models.issuer_policy import IssuerPolicy
from app.models.category import Category, CreditCardReward

class RoadmapEngine:
    """Engine for generating credit card roadmaps and portfolio recommendations."""
    
    def __init__(self, user_profile: UserProfile, user_cards: List[UserCard] = None):
        """Initialize the roadmap engine with user profile and current cards."""
        self.user_profile = user_profile
        self.user_cards = user_cards or []
        self.category_spending = user_profile.get_category_spending()
        self.monthly_spending = sum(self.category_spending.values())
        
    def generate_current_roadmap(self) -> Dict[str, Any]:
        """
        Generate roadmap showing which card to use for each category based on current portfolio.
        
        Returns:
            Dict containing category-to-card mapping and unused cards
        """
        category_recommendations = {}
        card_usage = defaultdict(list)  # Track which categories each card is best for
        
        # Get active user cards
        active_cards = [card for card in self.user_cards if card.is_active]
        
        if not active_cards:
            return {
                'category_recommendations': {},
                'card_usage': {},
                'message': 'No cards in portfolio - consider adding cards to optimize your spending'
            }
        
        # For each spending category, find the best card
        for category, monthly_spend in self.category_spending.items():
            if monthly_spend <= 0:
                continue
                
            best_card = None
            best_value = 0
            
            for user_card in active_cards:
                card = user_card.credit_card
                # Calculate monthly value for this category with this card
                monthly_value = self._calculate_monthly_category_value(card, category, monthly_spend)
                
                if monthly_value > best_value:
                    best_value = monthly_value
                    best_card = user_card
            
            if best_card:
                category_recommendations[category] = {
                    'card': best_card.to_dict(),
                    'monthly_value': best_value,
                    'annual_value': best_value * 12
                }
                card_usage[best_card.id].append({
                    'category': category,
                    'monthly_spend': monthly_spend,
                    'monthly_value': best_value
                })
        
        # Calculate total portfolio value
        total_annual_value = sum(rec['annual_value'] for rec in category_recommendations.values())
        total_annual_fees = sum(card.credit_card.annual_fee for card in active_cards)
        net_annual_value = total_annual_value - total_annual_fees
        
        return {
            'category_recommendations': category_recommendations,
            'card_usage': dict(card_usage),
            'portfolio_summary': {
                'total_annual_value': total_annual_value,
                'total_annual_fees': total_annual_fees,
                'net_annual_value': net_annual_value,
                'active_cards_count': len(active_cards)
            }
        }
    
    def generate_optimization_recommendations(self) -> Dict[str, Any]:
        """
        Generate recommendations for cards to apply for, cancel, or modify usage.
        
        Returns:
            Dict containing various recommendation types
        """
        recommendations = {
            'cards_to_apply': [],
            'cards_to_cancel': [],
            'spending_adjustments': [],
            'bonus_opportunities': []
        }
        
        # Find cards to cancel
        recommendations['cards_to_cancel'] = self._find_cards_to_cancel()
        
        # Find new cards to apply for
        recommendations['cards_to_apply'] = self._find_cards_to_apply()
        
        # Find bonus opportunities
        recommendations['bonus_opportunities'] = self._find_bonus_opportunities()
        
        return recommendations
    
    def generate_application_timeline(self, target_cards: List[int] = None) -> List[Dict[str, Any]]:
        """
        Generate a timeline for applying for new cards considering spending velocity and issuer policies.
        
        Args:
            target_cards: List of credit card IDs to apply for (if None, uses top recommendations)
        
        Returns:
            List of timeline events with dates and actions
        """
        if not target_cards:
            # Use top recommendations
            recommendations = self.generate_optimization_recommendations()
            target_cards = [card['card_id'] for card in recommendations['cards_to_apply'][:3]]
        
        timeline = []
        current_date = date.today()
        
        # Sort target cards by priority (highest value first)
        cards_with_priority = []
        for card_id in target_cards:
            card = CreditCard.query.get(card_id)
            if card:
                annual_value = self._calculate_annual_card_value(card)
                cards_with_priority.append((card, annual_value))
        
        cards_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        for card, value in cards_with_priority:
            # Check issuer policies
            policy_check = self._check_all_issuer_policies(card, current_date)
            
            if policy_check['can_apply']:
                apply_date = current_date
            else:
                apply_date = policy_check['next_eligible_date'] or current_date + timedelta(days=90)
            
            # Calculate minimum spend completion
            min_spend = card.signup_bonus_min_spend
            spend_months = min_spend / self.monthly_spending if self.monthly_spending > 0 else 3
            spend_completion_date = apply_date + relativedelta(months=int(spend_months) + 1)
            
            timeline.append({
                'date': apply_date,
                'action': 'apply',
                'card': card.to_dict() if hasattr(card, 'to_dict') else {'id': card.id, 'name': card.name},
                'reason': policy_check.get('reason', 'Optimal timing based on portfolio'),
                'expected_annual_value': value,
                'minimum_spend_required': min_spend,
                'estimated_spend_completion': spend_completion_date
            })
            
            # Update current date for next card consideration
            current_date = spend_completion_date
        
        return sorted(timeline, key=lambda x: x['date'])
    
    def _calculate_monthly_category_value(self, card: CreditCard, category: str, monthly_spend: float) -> float:
        """Calculate the monthly reward value for a specific category and spend amount."""
        # Get the reward rate for this category
        reward_rate = self._get_card_category_rate(card, category)
        
        # Apply reward value multiplier
        monthly_value = monthly_spend * reward_rate * card.reward_value_multiplier
        
        return monthly_value
    
    def _get_card_category_rate(self, card: CreditCard, category: str) -> float:
        """Get the reward rate for a specific category from a card."""
        # First check for specific reward relationships
        rewards = CreditCardReward.query.filter_by(credit_card_id=card.id).all()
        
        for reward in rewards:
            category_obj = Category.query.get(reward.category_id)
            if category_obj and category_obj.matches_category(category):
                return reward.reward_rate
        
        # Fall back to legacy fields or default rate
        category_rates = {
            'dining': getattr(card, 'dining_reward_rate', 0),
            'travel': getattr(card, 'travel_reward_rate', 0),
            'gas': getattr(card, 'gas_reward_rate', 0),
            'groceries': getattr(card, 'grocery_reward_rate', 0),
            'entertainment': getattr(card, 'entertainment_reward_rate', 0),
        }
        
        return category_rates.get(category, 0.01)  # Default 1% rate
    
    def _calculate_annual_card_value(self, card: CreditCard) -> float:
        """Calculate the annual value of a card for this user's spending."""
        annual_value = 0
        
        for category, monthly_spend in self.category_spending.items():
            monthly_value = self._calculate_monthly_category_value(card, category, monthly_spend)
            annual_value += monthly_value * 12
        
        # Add signup bonus value (amortized over first year)
        annual_value += card.signup_bonus_value
        
        # Subtract annual fee
        annual_value -= card.annual_fee
        
        return annual_value
    
    def _find_cards_to_cancel(self) -> List[Dict[str, Any]]:
        """Find cards that should be cancelled based on usage and fees."""
        cancel_recommendations = []
        
        current_roadmap = self.generate_current_roadmap()
        card_usage = current_roadmap.get('card_usage', {})
        
        for user_card in self.user_cards:
            if not user_card.is_active:
                continue
            
            card = user_card.credit_card
            annual_fee = card.annual_fee
            
            # Skip if no annual fee
            if annual_fee <= 0:
                continue
            
            # Check if card is being used optimally
            card_usage_info = card_usage.get(user_card.id, [])
            annual_value_from_usage = sum(cat['monthly_value'] * 12 for cat in card_usage_info)
            
            # Consider signup bonus status
            if not user_card.bonus_earned and not user_card.is_signup_bonus_expired:
                # Don't cancel if bonus is still achievable
                continue
            
            # Recommend cancellation if annual fee exceeds value
            if annual_fee > annual_value_from_usage + 50:  # $50 buffer
                cancel_recommendations.append({
                    'user_card_id': user_card.id,
                    'card': user_card.to_dict(),
                    'reason': f'Annual fee (${annual_fee}) exceeds value (${annual_value_from_usage:.2f})',
                    'annual_fee': annual_fee,
                    'annual_value': annual_value_from_usage,
                    'priority': 'high' if annual_fee > annual_value_from_usage + 200 else 'medium'
                })
        
        return sorted(cancel_recommendations, key=lambda x: x['annual_fee'] - x['annual_value'], reverse=True)
    
    def _find_cards_to_apply(self) -> List[Dict[str, Any]]:
        """Find new cards to apply for based on spending patterns."""
        apply_recommendations = []
        
        # Get all available cards not currently owned
        owned_card_ids = {uc.credit_card_id for uc in self.user_cards}
        available_cards = CreditCard.query.filter(
            ~CreditCard.id.in_(owned_card_ids),
            CreditCard.is_active == True
        ).all()
        
        # Check user constraints
        max_annual_fee = self.user_profile.max_annual_fee
        max_cards = self.user_profile.max_cards or 10
        
        for card in available_cards:
            # Check annual fee constraint
            if max_annual_fee and card.annual_fee > max_annual_fee:
                continue
            
            # Calculate potential value
            annual_value = self._calculate_annual_card_value(card)
            
            # Only recommend if value is significantly positive
            if annual_value > 100:  # Minimum $100 annual value
                # Check issuer policies
                policy_check = self._check_all_issuer_policies(card, date.today())
                
                apply_recommendations.append({
                    'card_id': card.id,
                    'card': card.to_dict() if hasattr(card, 'to_dict') else {'id': card.id, 'name': card.name},
                    'annual_value': annual_value,
                    'signup_bonus_value': card.signup_bonus_value,
                    'annual_fee': card.annual_fee,
                    'can_apply_now': policy_check['can_apply'],
                    'policy_restrictions': policy_check['restrictions'],
                    'next_eligible_date': policy_check.get('next_eligible_date'),
                    'priority': 'high' if annual_value > 500 else 'medium'
                })
        
        # Sort by annual value and return top recommendations
        apply_recommendations.sort(key=lambda x: x['annual_value'], reverse=True)
        return apply_recommendations[:max_cards - len(self.user_cards)]
    
    def _find_bonus_opportunities(self) -> List[Dict[str, Any]]:
        """Find signup bonus opportunities that are expiring or achievable."""
        bonus_opportunities = []
        
        for user_card in self.user_cards:
            card = user_card.credit_card
            
            # Skip if bonus already earned
            if user_card.bonus_earned:
                continue
            
            # Skip if bonus period expired
            if user_card.is_signup_bonus_expired:
                continue
            
            min_spend_required = user_card.effective_signup_bonus_min_spend
            bonus_value = user_card.effective_signup_bonus_value
            
            if min_spend_required <= 0 or bonus_value <= 0:
                continue
            
            # Calculate time to complete based on spending velocity
            months_to_complete = min_spend_required / self.monthly_spending if self.monthly_spending > 0 else 12
            deadline = user_card.signup_bonus_deadline
            
            if deadline:
                months_until_deadline = (deadline - date.today()).days / 30.44  # Average days per month
                
                bonus_opportunities.append({
                    'user_card_id': user_card.id,
                    'card': user_card.to_dict(),
                    'bonus_value': bonus_value,
                    'min_spend_required': min_spend_required,
                    'months_to_complete': months_to_complete,
                    'months_until_deadline': months_until_deadline,
                    'is_achievable': months_to_complete <= months_until_deadline,
                    'priority': 'high' if months_until_deadline <= 3 else 'medium'
                })
        
        return sorted(bonus_opportunities, key=lambda x: x['months_until_deadline'])
    
    def _check_all_issuer_policies(self, card: CreditCard, target_date: date) -> Dict[str, Any]:
        """Check all applicable issuer policies for a card application."""
        policies = IssuerPolicy.get_active_policies_for_issuer(card.issuer_id)
        
        policy_results = []
        can_apply = True
        next_eligible_date = None
        
        for policy in policies:
            result = policy.check_policy_compliance(self.user_cards, target_date)
            policy_results.append({
                'policy_name': policy.policy_name,
                'result': result
            })
            
            if not result['compliant']:
                can_apply = False
                if result.get('next_eligible_date'):
                    if not next_eligible_date or result['next_eligible_date'] > next_eligible_date:
                        next_eligible_date = result['next_eligible_date']
        
        return {
            'can_apply': can_apply,
            'restrictions': policy_results,
            'next_eligible_date': next_eligible_date
        }
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
        recommendations = []
        
        # Get all eligible cards based on filters
        eligible_cards = self._get_filtered_cards(roadmap)
        
        # Analyze current cards for keep/cancel/upgrade decisions
        current_card_recommendations = self._analyze_current_cards()
        recommendations.extend(current_card_recommendations)
        
        # Find new cards to apply for
        remaining_slots = max(0, roadmap.max_recommendations - len(current_card_recommendations))
        if remaining_slots > 0:
            new_card_recommendations = self._find_new_cards(eligible_cards, remaining_slots)
            recommendations.extend(new_card_recommendations)
        
        # Ensure we don't exceed max_recommendations
        return recommendations[:roadmap.max_recommendations]
    
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
                if '+' in filter_obj.value:
                    min_fee = int(filter_obj.value.replace('+', ''))
                    queryset = queryset.filter(annual_fee__gte=min_fee)
                elif '-' in filter_obj.value:
                    min_fee, max_fee = map(int, filter_obj.value.split('-'))
                    queryset = queryset.filter(annual_fee__gte=min_fee, annual_fee__lte=max_fee)
                else:
                    fee = int(filter_obj.value)
                    queryset = queryset.filter(annual_fee=fee)
        
        return list(queryset.prefetch_related('reward_categories', 'offers'))
    
    def _analyze_current_cards(self) -> List[dict]:
        """Analyze current cards for keep/cancel/upgrade recommendations"""
        recommendations = []
        
        for user_card in self.user_cards:
            card = user_card.card
            rewards_breakdown = self._calculate_card_rewards_breakdown(card)
            annual_rewards = rewards_breakdown['total_rewards']
            annual_fee = float(card.annual_fee)
            
            # Simple logic: keep if rewards > annual fee, otherwise consider canceling
            if annual_rewards > annual_fee + 50:  # $50 buffer
                action = 'keep'
                reasoning = f"Keep - earning ${annual_rewards:.0f} annually vs ${annual_fee} fee"
            elif annual_fee > 0 and annual_rewards < annual_fee:
                action = 'cancel'
                reasoning = f"Consider canceling - only earning ${annual_rewards:.0f} vs ${annual_fee} fee"
            else:
                action = 'keep'
                reasoning = f"Keep - earning ${annual_rewards:.0f} annually, reasonable for ${annual_fee} fee"
            
            recommendations.append({
                'card': card,
                'action': action,
                'estimated_rewards': Decimal(str(annual_rewards)),
                'reasoning': reasoning,
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'priority': 1 if action == 'cancel' else 2
            })
        
        return recommendations
    
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
            annual_fee = float(card.annual_fee)
            
            # Simple scoring: first year value
            first_year_value = annual_rewards + signup_bonus_value - annual_fee
            
            card_scores.append({
                'card': card,
                'score': first_year_value,
                'annual_rewards': annual_rewards,
                'signup_bonus': signup_bonus_value,
                'rewards_breakdown': rewards_breakdown['breakdown'],
                'reasoning': f"First year value: ${first_year_value:.0f} (${signup_bonus_value:.0f} bonus + ${annual_rewards:.0f} rewards - ${annual_fee} fee)"
            })
        
        # Sort by score and take top cards
        card_scores.sort(key=lambda x: x['score'], reverse=True)
        
        for i, card_data in enumerate(card_scores[:max_cards]):
            recommendations.append({
                'card': card_data['card'],
                'action': 'apply',
                'estimated_rewards': Decimal(str(card_data['score'])),
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
            recent_cards = UserCard.objects.filter(
                profile=self.profile,
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
        
        # Track which spending has been allocated to specific reward categories
        allocated_spending = 0.0
        
        # Calculate rewards for specific reward categories
        for reward_category in card.reward_categories.filter(is_active=True):
            category_slug = reward_category.category.slug
            annual_spend = all_spending.get(category_slug, 0.0)
            
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
        unallocated_spending = total_spending - allocated_spending
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
        
        return {
            'total_rewards': total_rewards,
            'breakdown': breakdown_details,
            'reward_multiplier': float(reward_value_multiplier)
        }
    
    def _get_signup_bonus_value(self, card: CreditCard) -> float:
        """Get signup bonus value using card's specific reward value multiplier"""
        if card.signup_bonus_amount:
            reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
            
            # All signup bonus amounts are stored as points/cents and need to be converted
            # using the card's specific reward value multiplier
            return float(card.signup_bonus_amount) * float(reward_value_multiplier)
        return 0.0
    
    def _calculate_total_rewards(self, recommendations: List[Dict]) -> Decimal:
        """Calculate total estimated rewards from all recommendations"""
        total = sum(rec.get('estimated_rewards', 0) for rec in recommendations)
        return Decimal(str(total))
    

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple
from django.db.models import Q, Sum
from cards.models import CreditCard, UserSpendingProfile, UserCard, Issuer, RewardCategory
from .models import Roadmap, RoadmapRecommendation, RoadmapCalculation


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
        
    def generate_roadmap(self, roadmap: Roadmap) -> List[RoadmapRecommendation]:
        """Generate recommendations for a roadmap"""
        recommendations = []
        
        # Get all eligible cards based on filters
        eligible_cards = self._get_filtered_cards(roadmap)
        
        # Analyze current cards for keep/cancel/upgrade decisions
        current_card_recommendations = self._analyze_current_cards()
        recommendations.extend(current_card_recommendations)
        
        # Find new cards to apply for
        new_card_recommendations = self._find_new_cards(
            eligible_cards, 
            roadmap.max_recommendations - len(current_card_recommendations)
        )
        recommendations.extend(new_card_recommendations)
        
        # Calculate total rewards and save
        total_rewards = self._calculate_total_rewards(recommendations)
        self._save_recommendations(roadmap, recommendations, total_rewards)
        
        return recommendations
    
    def _get_filtered_cards(self, roadmap: Roadmap) -> List[CreditCard]:
        """Apply roadmap filters to get eligible cards"""
        queryset = CreditCard.objects.filter(is_active=True)
        
        for filter_obj in roadmap.filters.all():
            if filter_obj.filter_type == 'issuer':
                queryset = queryset.filter(issuer__name__icontains=filter_obj.value)
            elif filter_obj.filter_type == 'reward_type':
                queryset = queryset.filter(primary_reward_type__name__icontains=filter_obj.value)
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
    
    def _analyze_current_cards(self) -> List[RoadmapRecommendation]:
        """Analyze current cards for keep/cancel/upgrade recommendations"""
        recommendations = []
        
        for user_card in self.user_cards:
            card = user_card.card
            annual_rewards = self._calculate_card_annual_rewards(card)
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
                'priority': 1 if action == 'cancel' else 2
            })
        
        return recommendations
    
    def _find_new_cards(self, eligible_cards: List[CreditCard], max_cards: int) -> List[RoadmapRecommendation]:
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
                
            annual_rewards = self._calculate_card_annual_rewards(card)
            signup_bonus_value = self._get_signup_bonus_value(card)
            annual_fee = float(card.annual_fee)
            
            # Simple scoring: first year value
            first_year_value = annual_rewards + signup_bonus_value - annual_fee
            
            card_scores.append({
                'card': card,
                'score': first_year_value,
                'annual_rewards': annual_rewards,
                'signup_bonus': signup_bonus_value,
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
        total_rewards = 0.0
        
        # Get the card's reward value multiplier (how much each point/mile is worth)
        reward_value_multiplier = card.metadata.get('reward_value_multiplier', 0.01)
        
        for reward_category in card.reward_categories.filter(is_active=True):
            category_slug = reward_category.category.slug
            monthly_spend = float(self.spending_amounts.get(category_slug, 0))
            annual_spend = monthly_spend * 12
            
            # Apply spending caps if they exist
            if reward_category.max_annual_spend:
                annual_spend = min(annual_spend, float(reward_category.max_annual_spend))
            
            reward_rate = float(reward_category.reward_rate)
            # Calculate points/miles earned: spend * rate
            points_earned = annual_spend * reward_rate
            # Convert to cash value using card's specific multiplier
            category_rewards = points_earned * float(reward_value_multiplier)
            total_rewards += category_rewards
        
        return total_rewards
    
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
    
    def _save_recommendations(self, roadmap: Roadmap, recommendations: List[Dict], total_rewards: Decimal):
        """Save recommendations to database"""
        # Clear existing recommendations
        roadmap.recommendations.all().delete()
        
        # Create new recommendations
        for rec_data in recommendations:
            RoadmapRecommendation.objects.create(
                roadmap=roadmap,
                **rec_data
            )
        
        # Save calculation
        RoadmapCalculation.objects.update_or_create(
            roadmap=roadmap,
            defaults={
                'total_estimated_rewards': total_rewards,
                'calculation_data': {
                    'recommendations_count': len(recommendations),
                    'calculated_at': datetime.now().isoformat(),
                    'spending_profile': {k: float(v) for k, v in self.spending_amounts.items()}
                }
            }
        )
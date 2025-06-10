"""Credit card recommendation engine."""
import json
import copy
import datetime
from typing import Dict, List, Any
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
import numpy as np
from datetime import datetime, timedelta

class RecommendationEngine:
    """Engine for generating credit card recommendations."""
    
    @staticmethod
    def calculate_card_value(card: CreditCard, profile: UserProfile) -> Dict[str, Any]:
        """
        Calculate the value of a credit card for a user profile.
        
        Args:
            card: The credit card to calculate value for
            profile: The user profile
            
        Returns:
            Dictionary containing value calculations
        """
        # Get spending by category
        category_spending = profile.get_category_spending()
        
        # Initialize variables for tracking value
        monthly_value = 0.0
        category_values = {}
        
        # Calculate value for each spending category
        for category, spend in category_spending.items():
            # Find the best reward rate for this category
            reward_rate = 0.0
            
            # Check category-specific rewards
            if category == 'dining' and card.dining_reward_rate > reward_rate:
                reward_rate = card.dining_reward_rate
            elif category == 'travel' and card.travel_reward_rate > reward_rate:
                reward_rate = card.travel_reward_rate
            elif category == 'gas' and card.gas_reward_rate > reward_rate:
                reward_rate = card.gas_reward_rate
            elif category == 'groceries' and card.grocery_reward_rate > reward_rate:
                reward_rate = card.grocery_reward_rate
            elif category == 'entertainment' and card.entertainment_reward_rate > reward_rate:
                reward_rate = card.entertainment_reward_rate
            
            # Default to base rate if no category rate is better
            if card.base_reward_rate > reward_rate:
                reward_rate = card.base_reward_rate
            
            # Calculate value for this category
            value = spend * reward_rate
            monthly_value += value
            category_values[category] = value
        
        # Calculate annual value
        annual_value = monthly_value * 12
        
        # Calculate value of sign-up bonus
        # Assume bonus is earned if monthly spend >= min spend / time limit
        signup_bonus_value = 0.0
        if card.signup_bonus_value > 0:
            total_monthly_spend = profile.total_monthly_spend
            required_monthly_spend = card.signup_bonus_min_spend / card.signup_bonus_time_limit * 30
            
            if total_monthly_spend >= required_monthly_spend:
                signup_bonus_value = card.signup_bonus_value
        
        # Calculate net value (including annual fee and sign-up bonus)
        net_value = annual_value + signup_bonus_value - card.annual_fee
        
        return {
            'card_id': card.id,
            'monthly_value': monthly_value,
            'annual_value': annual_value,
            'signup_bonus_value': signup_bonus_value,
            'annual_fee': card.annual_fee,
            'net_value': net_value,
            'category_values': category_values
        }

    @staticmethod
    def generate_recommendations(profile: UserProfile, available_cards: List[CreditCard]) -> Dict[str, Any]:
        """
        Generate credit card recommendations for a user profile.
        
        Args:
            profile: The user profile to generate recommendations for
            available_cards: List of available credit cards
            
        Returns:
            Dictionary containing recommendation data
        """
        # Calculate value for each card
        card_values = []
        for card in available_cards:
            # Skip credit score check since min_credit_score attribute doesn't exist
            # Instead, just calculate value for all cards
            
            # Calculate the card's value
            value_data = RecommendationEngine.calculate_card_value(card, profile)
            card_values.append(value_data)
        
        # Sort cards by net value (descending)
        card_values.sort(key=lambda x: x['net_value'], reverse=True)
        
        # Determine optimal card combination
        optimal_combination = RecommendationEngine.find_optimal_card_combination(
            card_values, 
            profile.max_cards, 
            profile.max_annual_fees,
            profile.get_category_spending()
        )
        
        # Calculate values over time
        per_month_value = RecommendationEngine.calculate_value_over_time(optimal_combination, 12)
        
        # Create recommendation data structure
        recommendation_data = {
            'profile_id': profile.id,
            'cards': [card['card_id'] for card in optimal_combination],
            'recommended_sequence': RecommendationEngine.determine_application_sequence(optimal_combination),
            'card_details': {str(card['card_id']): card for card in optimal_combination},
            'total_value': sum(card['net_value'] for card in optimal_combination),
            'total_annual_fees': sum(card['annual_fee'] for card in optimal_combination),
            'per_month_value': per_month_value,
            'spending_profile': profile.get_category_spending(),
            'card_preferences': profile.get_reward_preferences() if hasattr(profile, 'get_reward_preferences') else [],
            'generated_at': datetime.now().isoformat()
        }
        
        return recommendation_data

    @staticmethod
    def find_optimal_card_combination(
        card_values: List[Dict[str, Any]],
        max_cards: int,
        max_annual_fees: float,
        category_spending: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Find the optimal combination of credit cards.
        
        Args:
            card_values: List of card value calculations
            max_cards: Maximum number of cards to recommend
            max_annual_fees: Maximum total annual fees (0 if no limit)
            category_spending: Dictionary of spending by category
            
        Returns:
            List of optimal card value dictionaries
        """
        # If max_cards is 1, just return the best card that fits the annual fee constraint
        if max_cards == 1:
            for card in card_values:
                if max_annual_fees == 0 or card['annual_fee'] <= max_annual_fees:
                    return [card]
            return []
        
        # Initialize variables
        best_combination = []
        best_value = 0.0
        
        # Try all combinations using a greedy approach
        remaining_cards = card_values.copy()
        current_combination = []
        current_annual_fees = 0.0
        
        # Construct the combination
        while remaining_cards and len(current_combination) < max_cards:
            # Find the best card to add next
            best_next_card = None
            best_next_value = 0.0
            
            for i, card in enumerate(remaining_cards):
                # Check if adding this card would exceed the annual fee constraint
                if  max_annual_fees > 0 and current_annual_fees + card['annual_fee'] > max_annual_fees :
                    continue
                    
                # Calculate marginal value of adding this card
                marginal_value = RecommendationEngine.calculate_marginal_value(
                    card, 
                    current_combination,
                    category_spending
                )
                
                if marginal_value > best_next_value:
                    best_next_value = marginal_value
                    best_next_card = i
            
            # If no card can be added, break
            if best_next_card is None:
                break
                
            # Add the best card to the combination
            card = remaining_cards.pop(best_next_card)
            current_combination.append(card)
            current_annual_fees += card['annual_fee']
        
        # If resulting combination is better than the best found so far, update
        total_value = RecommendationEngine.calculate_total_combination_value(current_combination, category_spending)
        if total_value > best_value:
            best_combination = current_combination
            best_value = total_value
        
        return best_combination

    @staticmethod
    def calculate_marginal_value(
        card: Dict[str, Any], 
        current_cards: List[Dict[str, Any]],
        category_spending: Dict[str, float]
    ) -> float:
        """
        Calculate the marginal value of adding a card to a combination.
        
        Args:
            card: The card to add
            current_cards: The current card combination
            category_spending: Dictionary of spending by category
            
        Returns:
            The marginal value
        """
        # If there are no current cards, marginal value is the card's net value
        if not current_cards:
            return card['net_value']
        
        # Calculate value with and without the new card
        value_without = RecommendationEngine.calculate_total_combination_value(current_cards, category_spending)
        
        # Create a new combination with the card added
        new_combination = current_cards + [card]
        value_with = RecommendationEngine.calculate_total_combination_value(new_combination, category_spending)
        
        # Return the difference
        return value_with - value_without

    @staticmethod
    def calculate_total_combination_value(
        cards: List[Dict[str, Any]],
        category_spending: Dict[str, float]
    ) -> float:
        """
        Calculate the total value of a card combination, only counting the highest value per category from the best card for that category.
        Args:
            cards: List of card value calculations
            category_spending: Dictionary of spending by category
        Returns:
            The total value
        """
        # Guard clause for empty input
        if not cards:
            return 0.0

        # For each category, find the card with the highest value for that category
        total_category_value = 0.0
        if cards and cards[0].get('category_values'):
            categories = cards[0]['category_values'].keys()
            for category in categories:
                max_value = 0.0
                for card in cards:
                    value = card['category_values'].get(category, 0.0)
                    if value > max_value:
                        max_value = value
                total_category_value += max_value

        # Add signup bonuses and subtract annual fees for each card
        total_signup_bonus = sum(card.get('signup_bonus_value', 0.0) for card in cards)
        total_annual_fees = sum(card.get('annual_fee', 0.0) for card in cards)

        # Annualize the category value (since category_values are monthly)
        annual_category_value = total_category_value * 12

        total_value = annual_category_value + total_signup_bonus - total_annual_fees
        return total_value

    @staticmethod
    def determine_application_sequence(cards: List[Dict[str, Any]]) -> List[int]:
        """
        Determine the optimal sequence for applying to cards.
        
        Args:
            cards: List of card value calculations
            
        Returns:
            List of card IDs in recommended application order
        """
        # For now, just order by net value (highest first)
        sorted_cards = sorted(cards, key=lambda x: x['net_value'], reverse=True)
        return [card['card_id'] for card in sorted_cards]

    @staticmethod
    def calculate_value_over_time(cards: List[Dict[str, Any]], months: int) -> List[float]:
        """
        Calculate the cumulative value over time.
        
        Args:
            cards: List of card value calculations
            months: Number of months to calculate for
            
        Returns:
            List of cumulative values by month
        """
        # Initialize array for monthly values
        monthly_values = np.zeros(months)
        
        # Add up monthly values from each card
        for card in cards:
            # Add recurring monthly value
            monthly_values += card['monthly_value']
            
            # Add sign-up bonus (assume received in first month)
            if card['signup_bonus_value'] > 0:
                monthly_values[0] += card['signup_bonus_value']
            
            # Subtract annual fee (assume paid in first month)
            if card['annual_fee'] > 0:
                monthly_values[0] -= card['annual_fee']
        
        # Calculate cumulative values
        cumulative_values = np.cumsum(monthly_values)
        
        return cumulative_values.tolist() 
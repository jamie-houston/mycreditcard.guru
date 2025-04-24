from typing import List, Dict, Any, Tuple
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
import json

def calculate_card_value(
    card: CreditCard, 
    profile: UserProfile
) -> float:
    """
    Calculate the estimated value of a credit card based on user spending patterns.
    
    Args:
        card: The credit card to evaluate
        profile: The user profile with spending data
        
    Returns:
        float: The estimated annual value of the card
    """
    value = 0.0
    
    # Parse JSON data
    try:
        reward_categories = json.loads(card.reward_categories)
        offers = json.loads(card.offers)
        category_spending = json.loads(profile.category_spending)
        reward_preferences = json.loads(profile.reward_preferences)
    except (json.JSONDecodeError, TypeError):
        # Default to empty collections if JSON parsing fails
        reward_categories = []
        offers = []
        category_spending = {}
        reward_preferences = []
    
    # Calculate value from reward categories
    for category in reward_categories:
        category_name = category.get('category')
        reward_percentage = category.get('percentage', 0)
        
        # Check if user has spending in this category
        category_spend = category_spending.get(category_name, 0)
        
        # Calculate annual value from this category (monthly spend * 12 * reward percentage)
        category_value = category_spend * 12 * (reward_percentage / 100)
        value += category_value
    
    # Add value from card offers
    for offer in offers:
        offer_type = offer.get('type')
        offer_amount = offer.get('amount', 0)
        offer_frequency = offer.get('frequency', 'one_time')
        
        # Only count offers that match user preferences
        if offer_type in reward_preferences:
            if offer_frequency == 'annual':
                value += offer_amount
            elif offer_frequency == 'monthly':
                value += offer_amount * 12
            else:  # one_time
                value += offer_amount / 2  # Amortize one-time offers over 2 years
    
    # Add signup bonus value (amortized over 2 years)
    value += card.signup_bonus_value / 2
    
    # Subtract annual fee
    value -= card.annual_fee
    
    return value

def generate_card_recommendations(
    profile: UserProfile, 
    cards: List[CreditCard], 
    max_cards: int = 5, 
    max_annual_fees: float = 0.0
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Generate credit card recommendations based on user profile.
    
    Args:
        profile: The user profile
        cards: List of available credit cards
        max_cards: Maximum number of cards to recommend
        max_annual_fees: Maximum annual fees the user is willing to pay
        
    Returns:
        Tuple containing:
        - List of recommended cards with timing
        - Total estimated value
    """
    # Calculate value for each card
    card_values = []
    for card in cards:
        value = calculate_card_value(card, profile)
        card_values.append({
            'card': card,
            'value': value
        })
    
    # Sort cards by value
    card_values.sort(key=lambda x: x['value'], reverse=True)
    
    # Select top cards within constraints
    selected_cards = []
    total_annual_fees = 0.0
    
    for item in card_values:
        if len(selected_cards) >= max_cards:
            break
            
        card = item['card']
        
        # Check if adding this card would exceed annual fee limit
        if total_annual_fees + card.annual_fee > max_annual_fees and max_annual_fees > 0:
            continue
            
        selected_cards.append(item)
        total_annual_fees += card.annual_fee
    
    # Generate timeline for card applications (simplified)
    # In a real implementation, this would be more sophisticated
    recommendations = []
    total_value = 0.0
    
    for i, item in enumerate(selected_cards):
        card = item['card']
        value = item['value']
        
        # Simple timeline: space cards 3 months apart
        signup_month = i * 3 + 1
        
        # For high annual fee cards, recommend canceling after 1 year
        cancel_month = signup_month + 12 if card.annual_fee > 100 else None
        
        recommendations.append({
            'card_id': card.id,
            'signup_month': signup_month,
            'cancel_month': cancel_month,
            'estimated_value': value
        })
        
        total_value += value
    
    return recommendations, total_value 
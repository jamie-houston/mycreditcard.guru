from creditcard_roadmap.app.models import CreditCard, Profile
from sqlalchemy import and_
import numpy as np
from typing import List, Dict, Any, Optional
import itertools
from creditcard_roadmap.app import db
import copy
import logging

logger = logging.getLogger(__name__)

def calculate_card_value(profile: Profile, card: CreditCard) -> Dict[str, Any]:
    """
    Calculate the value of a credit card for a given spending profile
    
    Returns:
        Dict with value breakdown and total value
    """
    # Calculate monthly rewards by category
    dining_value = profile.dining_spend * (card.dining_reward_rate or card.base_reward_rate)
    travel_value = profile.travel_spend * (card.travel_reward_rate or card.base_reward_rate)
    gas_value = profile.gas_spend * (card.gas_reward_rate or card.base_reward_rate)
    grocery_value = profile.grocery_spend * (card.grocery_reward_rate or card.base_reward_rate)
    entertainment_value = profile.entertainment_spend * (card.entertainment_reward_rate or card.base_reward_rate)
    other_value = profile.other_spend * card.base_reward_rate
    
    # Calculate annual value (12 months)
    annual_value = 12 * (dining_value + travel_value + gas_value + grocery_value + entertainment_value + other_value)
    
    # Calculate sign-up bonus value
    # Assume bonus is achieved if total spend over bonus_time_limit months exceeds min_spend
    months_to_hit_bonus = min(
        card.signup_bonus_time_limit,
        max(1, card.signup_bonus_min_spend / profile.total_monthly_spend)
    ) if card.signup_bonus_min_spend > 0 and profile.total_monthly_spend > 0 else 0
    
    signup_bonus_value = card.signup_bonus_value if months_to_hit_bonus <= card.signup_bonus_time_limit else 0
    
    # Total first-year value
    net_value = annual_value + signup_bonus_value - card.annual_fee
    
    # Calculate monthly values for the first year
    monthly_values = []
    for month in range(12):
        month_value = (dining_value + travel_value + gas_value + grocery_value + entertainment_value + other_value)
        # Add signup bonus in the month it would be earned
        if month + 1 == round(months_to_hit_bonus) and signup_bonus_value > 0:
            month_value += signup_bonus_value
        # Subtract annual fee in first month
        if month == 0:
            month_value -= card.annual_fee
        monthly_values.append(month_value)
        
    return {
        'annual_value': annual_value,
        'signup_bonus_value': signup_bonus_value,
        'annual_fee': card.annual_fee,
        'net_value': net_value,
        'category_values': {
            'dining': dining_value,
            'travel': travel_value,
            'gas': gas_value,
            'grocery': grocery_value,
            'entertainment': entertainment_value,
            'other': other_value
        },
        'monthly_values': monthly_values
    }

def generate_recommendations(
    profile: Profile,
    max_cards: int = 1,
    max_annual_fees: float = 500.0,
    card_types: Optional[List[str]] = None,
    networks: Optional[List[str]] = None,
    include_business: bool = False
) -> Dict[str, Any]:
    """
    Generate credit card recommendations based on a user's spending profile
    
    Args:
        profile: The user's spending profile
        max_cards: Maximum number of cards to recommend
        max_annual_fees: Maximum total annual fees for all cards
        card_types: Filter for specific card types
        networks: Filter for specific card networks
        include_business: Whether to include business cards in recommendations
        
    Returns:
        Dictionary containing recommendation data
    """
    # Get all eligible cards
    query = CreditCard.query
    
    # Apply filters
    filters = []
    
    # Filter by card type (cash back, travel, etc.)
    if card_types:
        filters.append(CreditCard.card_type.in_(card_types))
    
    # Filter by network (visa, mastercard, etc.)
    if networks:
        filters.append(CreditCard.network.in_(networks))
    
    # Filter by minimum credit score
    filters.append(CreditCard.min_credit_score <= profile.credit_score)
    
    # Filter by business cards
    if not include_business:
        filters.append(CreditCard.is_business == False)
    
    # Apply all filters
    if filters:
        query = query.filter(and_(*filters))
    
    # Get all eligible cards
    all_cards = query.all()
    
    # Calculate the value of each card for this profile
    card_values = []
    for card in all_cards:
        value_info = calculate_card_value(profile, card)
        
        # Store the card and its value
        card_values.append({
            'card': card,
            'annual_value': value_info['annual_value'],
            'signup_bonus_value': value_info['signup_bonus_value'],
            'annual_fee': value_info['annual_fee'],
            'net_value': value_info['net_value'],
            'category_values': value_info['category_values'],
            'overall_value': value_info['net_value']  # Overall value = net value including signup bonus
        })
    
    # Sort by overall value (first year value)
    card_values.sort(key=lambda x: x['overall_value'], reverse=True)
    
    # Select top cards based on constraints
    selected_cards = []
    total_annual_fees = 0
    
    for card_value in card_values:
        # Check if we've reached the maximum number of cards
        if len(selected_cards) >= max_cards:
            break
        
        # Check if adding this card would exceed the annual fee limit
        if total_annual_fees + card_value['annual_fee'] > max_annual_fees:
            continue
        
        # Add the card
        selected_cards.append(card_value)
        total_annual_fees += card_value['annual_fee']
    
    # Generate the recommendation output
    recommended_sequence = [card_value['card'].id for card_value in selected_cards]
    
    # Calculate the total value
    total_value = sum(card_value['net_value'] for card_value in selected_cards)
    
    # Calculate the value per month over the first year
    per_month_value = calculate_monthly_values(selected_cards, profile)
    
    # Prepare card details for storage
    card_details = {}
    for card_value in selected_cards:
        card_id = str(card_value['card'].id)
        card_details[card_id] = {
            'annual_value': card_value['annual_value'],
            'signup_bonus_value': card_value['signup_bonus_value'],
            'annual_fee': card_value['annual_fee'],
            'net_value': card_value['net_value'],
            'category_values': card_value['category_values']
        }
    
    # Prepare the return data
    recommendation_data = {
        'recommended_sequence': recommended_sequence,
        'total_value': total_value,
        'total_annual_fees': total_annual_fees,
        'per_month_value': per_month_value,
        'card_details': card_details
    }
    
    return recommendation_data

def calculate_monthly_values(selected_cards: List[Dict], profile: Profile) -> List[float]:
    """
    Calculate the cumulative value of a set of cards over each month in the first year
    
    Args:
        selected_cards: List of selected card value objects
        profile: The user's spending profile
        
    Returns:
        List of cumulative values for each month
    """
    # Initialize monthly values
    monthly_values = [0.0] * 12
    
    for card_value in selected_cards:
        card = card_value['card']
        monthly_reward = sum(card_value['category_values'].values())
        
        # Add monthly rewards value
        for i in range(12):
            monthly_values[i] += monthly_reward
        
        # Add signup bonus in the month it would be received
        if profile.total_monthly_spend * card.signup_bonus_time_limit >= card.signup_bonus_min_spend:
            # Assume signup bonus is received after the minimum spend period
            min_spend_months = max(1, int(card.signup_bonus_min_spend / profile.total_monthly_spend))
            bonus_month = min(11, min_spend_months)  # Ensure we don't go beyond 12 months
            monthly_values[bonus_month] += card_value['signup_bonus_value']
        
        # Subtract annual fee in the first month
        monthly_values[0] -= card_value['annual_fee']
    
    # Convert to cumulative values
    cumulative_values = []
    current_sum = 0
    for value in monthly_values:
        current_sum += value
        cumulative_values.append(current_sum)
    
    return cumulative_values

def calculate_card_sequence_value(card_sequence: List[int], cards_data: Dict[int, Dict[str, float]],
                                 max_cards: int = 3) -> Dict[str, Any]:
    """Calculate the total value of a sequence of cards over time"""
    
    if len(card_sequence) > max_cards:
        card_sequence = card_sequence[:max_cards]
    
    total_annual_value = sum(cards_data[card_id]['annual_value'] for card_id in card_sequence)
    total_signup_value = sum(cards_data[card_id]['signup_bonus_value'] for card_id in card_sequence)
    total_annual_fees = sum(cards_data[card_id]['annual_fee'] for card_id in card_sequence)
    
    # Calculate monthly progressive value (simple model: signup bonuses spread over first 3 months)
    monthly_values = []
    cumulative_value = 0
    
    for month in range(12):
        month_value = total_annual_value / 12
        
        # Add signup bonuses over first 3 months
        if month < 3 and total_signup_value > 0:
            month_value += total_signup_value / 3
        
        cumulative_value += month_value
        monthly_values.append(round(cumulative_value, 2))
    
    return {
        'card_sequence': card_sequence,
        'total_annual_value': total_annual_value,
        'total_signup_value': total_signup_value,
        'total_annual_fees': total_annual_fees,
        'total_value': total_annual_value + total_signup_value - total_annual_fees,
        'per_month_value': monthly_values
    }

def generate_card_recommendations(profile: Profile, max_cards: int = 1, 
                                max_annual_fees: float = 1000) -> Dict[str, Any]:
    """Generate credit card recommendations based on user spending profile"""
    
    logger.info(f"Generating recommendations for profile {profile.id}")
    
    # Get all available credit cards
    cards = CreditCard.query.all()
    logger.info(f"Found {len(cards)} cards to evaluate")
    
    # Calculate value for each card
    cards_value_data = {}
    for card in cards:
        card_value = calculate_card_value(profile, card)
        cards_value_data[card.id] = card_value
    
    # Sort cards by net value (annual value + signup bonus - annual fee)
    sorted_cards = sorted(
        cards_value_data.keys(),
        key=lambda card_id: (
            cards_value_data[card_id]['annual_value'] + 
            cards_value_data[card_id]['signup_bonus_value'] - 
            cards_value_data[card_id]['annual_fee']
        ),
        reverse=True
    )
    
    # Generate the recommended sequence
    recommended_sequence = []
    current_annual_fees = 0
    
    for card_id in sorted_cards:
        if len(recommended_sequence) >= max_cards:
            break
            
        card_fee = cards_value_data[card_id]['annual_fee']
        
        # Skip if adding this card would exceed max annual fees
        if current_annual_fees + card_fee > max_annual_fees:
            continue
            
        recommended_sequence.append(card_id)
        current_annual_fees += card_fee
    
    # Calculate overall sequence value
    sequence_data = calculate_card_sequence_value(
        recommended_sequence, 
        cards_value_data,
        max_cards=max_cards
    )
    
    # Create final recommendation data
    recommendation_data = {
        'recommended_sequence': recommended_sequence,
        'total_value': sequence_data['total_value'],
        'total_annual_fees': sequence_data['total_annual_fees'],
        'per_month_value': sequence_data['per_month_value'],
        'card_details': {
            str(card_id): {
                'annual_value': cards_value_data[card_id]['annual_value'],
                'signup_bonus_value': cards_value_data[card_id]['signup_bonus_value'],
                'annual_fee': cards_value_data[card_id]['annual_fee']
            } for card_id in recommended_sequence
        }
    }
    
    logger.info(f"Generated recommendation with {len(recommended_sequence)} cards")
    return recommendation_data 
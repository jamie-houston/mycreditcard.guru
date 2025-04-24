from typing import Dict, List, Any
from app.models.credit_card import CreditCard
from app.models.user_profile import UserProfile
import numpy as np
from flask import current_app
from sqlalchemy import desc

def calculate_annual_category_value(spend_amount: float, reward_rate: float) -> float:
    """Calculate the annual value of rewards for a spending category."""
    return spend_amount * reward_rate

def calculate_card_value_for_profile(card: CreditCard, profile: UserProfile) -> Dict[str, Any]:
    """Calculate the value of a credit card based on a user's spending profile."""
    rewards_by_category = {}
    
    # Base rewards (all other spending)
    other_spending = profile.other_spending
    base_value = calculate_annual_category_value(other_spending, card.base_reward_rate)
    rewards_by_category['other'] = base_value
    
    # Category-specific rewards
    if card.dining_reward_rate and profile.dining_spending:
        dining_value = calculate_annual_category_value(profile.dining_spending, card.dining_reward_rate)
        rewards_by_category['dining'] = dining_value
    
    if card.travel_reward_rate and profile.travel_spending:
        travel_value = calculate_annual_category_value(profile.travel_spending, card.travel_reward_rate)
        rewards_by_category['travel'] = travel_value
    
    if card.gas_reward_rate and profile.gas_spending:
        gas_value = calculate_annual_category_value(profile.gas_spending, card.gas_reward_rate)
        rewards_by_category['gas'] = gas_value
    
    if card.grocery_reward_rate and profile.grocery_spending:
        grocery_value = calculate_annual_category_value(profile.grocery_spending, card.grocery_reward_rate)
        rewards_by_category['grocery'] = grocery_value
    
    if card.entertainment_reward_rate and profile.entertainment_spending:
        entertainment_value = calculate_annual_category_value(profile.entertainment_spending, card.entertainment_reward_rate)
        rewards_by_category['entertainment'] = entertainment_value
    
    # Calculate total rewards value
    total_rewards_value = sum(rewards_by_category.values())
    
    # Include signup bonus in first-year value
    first_year_value = total_rewards_value - card.annual_fee
    if card.signup_bonus_value:
        first_year_value += card.signup_bonus_value
    
    return {
        'rewards_by_category': rewards_by_category,
        'total_rewards_value': total_rewards_value,
        'annual_value': first_year_value,
        'annual_fee': card.annual_fee,
        'signup_bonus': card.signup_bonus_value
    }

def generate_recommendations(profile: UserProfile) -> Dict[str, Any]:
    """Generate credit card recommendations based on a user's spending profile."""
    # Get all available credit cards
    cards = CreditCard.query.filter_by(active=True).all()
    
    # Calculate value of each card for the user's profile
    card_values = {}
    for card in cards:
        # Skip cards requiring a higher credit score than the user has
        if (profile.credit_score == 'poor' and card.credit_score_required != 'poor') or \
           (profile.credit_score == 'fair' and card.credit_score_required not in ['poor', 'fair']) or \
           (profile.credit_score == 'good' and card.credit_score_required == 'excellent'):
            continue
        
        card_value = calculate_card_value_for_profile(card, profile)
        
        # Only include cards with positive value
        if card_value['annual_value'] > 0:
            card_values[card.id] = card_value
    
    # Sort cards by annual value (descending)
    sorted_card_ids = sorted(card_values.keys(), key=lambda x: card_values[x]['annual_value'], reverse=True)
    
    # Limit to top 5 cards
    recommended_sequence = sorted_card_ids[:5]
    
    # Calculate total value and fees
    total_value = sum(card_values[card_id]['annual_value'] for card_id in recommended_sequence)
    total_annual_fees = sum(card_values[card_id]['annual_fee'] for card_id in recommended_sequence)
    
    # Calculate monthly value distribution (simplified for now)
    monthly_values = []
    cumulative_value = 0
    
    # First month includes all signup bonuses
    first_month_value = sum(card_values[card_id].get('signup_bonus', 0) for card_id in recommended_sequence)
    
    # Monthly spending rewards distributed evenly (excluding signup bonuses)
    monthly_rewards = sum(card_values[card_id]['total_rewards_value'] - card_values[card_id]['annual_fee'] 
                          for card_id in recommended_sequence) / 12
    
    # Calculate cumulative value by month
    for month in range(12):
        if month == 0:
            # First month: signup bonuses + regular rewards - annual fees
            cumulative_value = first_month_value + monthly_rewards
        else:
            # Subsequent months: just add regular rewards
            cumulative_value += monthly_rewards
        
        monthly_values.append(round(cumulative_value, 2))
    
    return {
        'recommended_sequence': recommended_sequence,
        'card_details': card_values,
        'total_value': total_value,
        'total_annual_fees': total_annual_fees,
        'per_month_value': monthly_values
    } 
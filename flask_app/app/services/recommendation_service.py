from datetime import datetime
from app.models.recommendation import Recommendation
import numpy as np

def generate_recommendation(profile, user, available_cards):
    """
    Generate credit card recommendations based on user spending profile.
    
    Args:
        profile: UserProfile object containing spending information
        user: Current user
        available_cards: Dictionary of available credit cards {id: card_dict}
        
    Returns:
        Recommendation object containing recommended cards and value calculations
    """
    # Extract spending information from profile
    monthly_spending = {
        'dining': profile.monthly_dining_spend or 0,
        'travel': profile.monthly_travel_spend or 0,
        'gas': profile.monthly_gas_spend or 0,
        'grocery': profile.monthly_grocery_spend or 0,
        'entertainment': profile.monthly_entertainment_spend or 0,
        'other': profile.monthly_other_spend or 0
    }
    
    # Calculate total monthly spending
    total_monthly_spend = sum(monthly_spending.values())
    total_annual_spend = total_monthly_spend * 12
    
    # Calculate annual spending by category
    annual_spending = {category: amount * 12 for category, amount in monthly_spending.items()}
    
    # Find the best card combination
    recommended_cards, card_details, total_value, per_month_value = optimize_card_combination(
        available_cards, 
        annual_spending,
        max_cards=profile.max_cards or 1  # Use profile's max_cards setting
    )
    
    # Calculate total annual fees
    total_annual_fees = sum(available_cards[card_id]['annual_fee'] for card_id in recommended_cards)
    
    # Create and return a recommendation object
    recommendation = Recommendation(
        user_id=user.id,
        profile_id=profile.id,
        created_at=datetime.now(),
        recommended_sequence=recommended_cards,
        card_details=card_details,
        total_value=total_value,
        total_annual_fees=total_annual_fees,
        card_count=len(recommended_cards),
        per_month_value=per_month_value
    )
    
    return recommendation

def calculate_card_value(card, annual_spending):
    """
    Calculate the annual value of a credit card based on spending profile.
    
    Args:
        card: Credit card dictionary
        annual_spending: Dictionary of annual spending by category
        
    Returns:
        annual_value: Total annual value of the card
        rewards_by_category: Breakdown of rewards by spending category
    """
    rewards_by_category = {}
    
    # Calculate rewards for each spending category
    rewards_by_category['dining'] = annual_spending['dining'] * card.get('dining_reward_rate', card['base_reward_rate'])
    rewards_by_category['travel'] = annual_spending['travel'] * card.get('travel_reward_rate', card['base_reward_rate'])
    rewards_by_category['gas'] = annual_spending['gas'] * card.get('gas_reward_rate', card['base_reward_rate'])
    rewards_by_category['grocery'] = annual_spending['grocery'] * card.get('grocery_reward_rate', card['base_reward_rate'])
    rewards_by_category['entertainment'] = annual_spending['entertainment'] * card.get('entertainment_reward_rate', card['base_reward_rate'])
    rewards_by_category['other'] = annual_spending['other'] * card['base_reward_rate']
    
    # Add signup bonus value (assuming it's earned in the first year)
    signup_bonus = card.get('signup_bonus_value', 0)
    
    # Calculate total annual value (rewards - annual fee + signup bonus)
    total_rewards = sum(rewards_by_category.values())
    annual_value = total_rewards - card['annual_fee'] + signup_bonus
    
    return annual_value, rewards_by_category

def optimize_card_combination(available_cards, annual_spending, max_cards=1):
    """
    Find the optimal combination of credit cards that maximizes total value.
    
    Args:
        available_cards: Dictionary of available credit cards {id: card_dict}
        annual_spending: Dictionary of annual spending by category
        max_cards: Maximum number of cards to recommend
        
    Returns:
        recommended_cards: List of card IDs in recommended order
        card_details: Dictionary of details for each recommended card
        total_value: Total annual value of the card combination
        per_month_value: List of cumulative values for each month in the first year
    """
    # Calculate value for each card individually
    card_values = {}
    for card_id, card in available_cards.items():
        annual_value, rewards_by_category = calculate_card_value(card, annual_spending)
        card_values[card_id] = {
            'annual_value': annual_value,
            'rewards_by_category': rewards_by_category
        }
    
    # Sort cards by annual value
    sorted_cards = sorted(card_values.items(), key=lambda x: x[1]['annual_value'], reverse=True)
    
    # Take top max_cards cards
    recommended_cards = [card_id for card_id, _ in sorted_cards[:max_cards]]
    card_details = {card_id: card_values[card_id] for card_id in recommended_cards}
    
    # Calculate total value
    total_value = sum(card_details[card_id]['annual_value'] for card_id in recommended_cards)
    
    # Calculate value over time (per month for the first year)
    monthly_values = calculate_monthly_values(recommended_cards, available_cards, annual_spending)
    
    return recommended_cards, card_details, total_value, monthly_values

def calculate_monthly_values(card_ids, available_cards, annual_spending):
    """
    Calculate the cumulative value of cards for each month in the first year.
    
    Args:
        card_ids: List of card IDs
        available_cards: Dictionary of available credit cards
        annual_spending: Dictionary of annual spending by category
        
    Returns:
        monthly_values: List of cumulative values for each month
    """
    monthly_spending = {category: amount / 12 for category, amount in annual_spending.items()}
    monthly_values = [0] * 12
    
    for month in range(12):
        # Monthly rewards from regular spending
        month_value = 0
        
        for card_id in card_ids:
            card = available_cards[card_id]
            
            # Add regular rewards for this month
            dining_rewards = monthly_spending['dining'] * card.get('dining_reward_rate', card['base_reward_rate'])
            travel_rewards = monthly_spending['travel'] * card.get('travel_reward_rate', card['base_reward_rate'])
            gas_rewards = monthly_spending['gas'] * card.get('gas_reward_rate', card['base_reward_rate'])
            grocery_rewards = monthly_spending['grocery'] * card.get('grocery_reward_rate', card['base_reward_rate'])
            entertainment_rewards = monthly_spending['entertainment'] * card.get('entertainment_reward_rate', card['base_reward_rate'])
            other_rewards = monthly_spending['other'] * card['base_reward_rate']
            
            monthly_reward = dining_rewards + travel_rewards + gas_rewards + grocery_rewards + entertainment_rewards + other_rewards
            
            # Add signup bonus if applicable (in the month after signup_bonus_time_limit)
            if month == card.get('signup_bonus_time_limit', 3) and card.get('signup_bonus_value', 0) > 0:
                monthly_reward += card.get('signup_bonus_value', 0)
            
            # Subtract annual fee (only in first month)
            if month == 0:
                monthly_reward -= card['annual_fee']
            
            month_value += monthly_reward
        
        # Add to cumulative value
        if month == 0:
            monthly_values[month] = month_value
        else:
            monthly_values[month] = monthly_values[month - 1] + month_value
    
    return monthly_values 
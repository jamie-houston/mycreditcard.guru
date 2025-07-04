#!/usr/bin/env python3
"""
Script to convert data.json into separate files for each issuer.
Maps the original data structure to the format expected by the Django app.
"""

import json
import os
from collections import defaultdict

def map_issuer_name(issuer):
    """Map issuer names to consistent format"""
    issuer_mapping = {
        'AMERICAN_EXPRESS': 'American Express',
        'CHASE': 'Chase',
        'CAPITAL_ONE': 'Capital One',
        'CITI': 'Citi',
        'DISCOVER': 'Discover',
        'WELLS_FARGO': 'Wells Fargo',
        'BANK_OF_AMERICA': 'Bank of America',
        'US_BANK': 'US Bank',
        'BARCLAYS': 'Barclays',
        'SYNCHRONY': 'Synchrony'
    }
    return issuer_mapping.get(issuer, issuer.replace('_', ' ').title())

def map_reward_type(card_data):
    """Determine reward type based on card data"""
    if card_data.get('universalCashbackPercent'):
        return 'Cashback'
    elif 'miles' in card_data.get('name', '').lower():
        return 'Miles'
    else:
        return 'Points'

def extract_reward_categories(card_data):
    """Extract reward categories from the card data"""
    categories = []
    
    # Add universal cashback as "other" category
    universal_rate = card_data.get('universalCashbackPercent', 0)
    if universal_rate > 0:
        categories.append({
            "category": "other",
            "reward_rate": universal_rate
        })
    
    # TODO: Add specific category parsing if available in the data
    # The current data structure doesn't seem to have detailed category breakdowns
    # This would need to be enhanced based on the actual data structure
    
    return categories

def convert_card(card_data):
    """Convert a single card from the original format to our format"""
    # Extract signup bonus info
    signup_bonus = {}
    if card_data.get('offers') and len(card_data['offers']) > 0:
        offer = card_data['offers'][0]  # Take the first/current offer
        signup_bonus = {
            "bonus_amount": offer.get('amount', [{}])[0].get('amount', 0),
            "spending_requirement": offer.get('spend', 0),
            "time_limit_months": offer.get('days', 90) // 30  # Convert days to months
        }
    
    # Map reward value multiplier based on reward type
    reward_type = map_reward_type(card_data)
    if reward_type == 'Cashback':
        multiplier = 0.01  # 1 cent per point
    elif reward_type == 'Miles':
        multiplier = 0.012  # 1.2 cents per mile (average)
    else:
        multiplier = 0.01  # 1 cent per point (default)
    
    return {
        "name": card_data.get('name', ''),
        "issuer": map_issuer_name(card_data.get('issuer', '')),
        "annual_fee": card_data.get('annualFee', 0),
        "signup_bonus": signup_bonus if signup_bonus.get('bonus_amount', 0) > 0 else None,
        "reward_type": reward_type,
        "reward_value_multiplier": multiplier,
        "reward_categories": extract_reward_categories(card_data),
        "card_type": "business" if card_data.get('isBusiness', False) else "personal",
        "network": card_data.get('network', '').replace('_', ' ').title(),
        "url": card_data.get('url', ''),
        "image_url": card_data.get('imageUrl', ''),
        "discontinued": card_data.get('discontinued', False)
    }

def main():
    # Read the data.json file
    input_file = 'data/input/data.json'
    output_dir = 'data/input'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r') as f:
        cards_data = json.load(f)
    
    print(f"Found {len(cards_data)} cards")
    
    # Group cards by issuer
    cards_by_issuer = defaultdict(list)
    
    for card_data in cards_data:
        if card_data.get('discontinued', False):
            print(f"Skipping discontinued card: {card_data.get('name', 'Unknown')}")
            continue
            
        converted_card = convert_card(card_data)
        issuer = converted_card['issuer']
        cards_by_issuer[issuer].append(converted_card)
    
    # Write separate files for each issuer
    for issuer, cards in cards_by_issuer.items():
        # Create a safe filename
        safe_issuer = issuer.lower().replace(' ', '_').replace('&', 'and')
        filename = f"{output_dir}/{safe_issuer}.json"
        
        print(f"Writing {len(cards)} cards to {filename}")
        
        with open(filename, 'w') as f:
            json.dump(cards, f, indent=2)
    
    print(f"\nConversion complete! Created files for {len(cards_by_issuer)} issuers:")
    for issuer, cards in cards_by_issuer.items():
        safe_issuer = issuer.lower().replace(' ', '_').replace('&', 'and')
        print(f"  - {safe_issuer}.json ({len(cards)} cards)")

if __name__ == '__main__':
    main()
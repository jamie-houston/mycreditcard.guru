#!/usr/bin/env python
"""
Seed Credit Cards

This script seeds the database with sample credit cards for development and testing.
Creates example credit cards with different reward structures and features.
"""

import sys
import os
import json

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
from app.models import CardIssuer

def seed_credit_cards():
    """Seed the database with sample credit cards."""
    
    # Sample credit cards data - expanded from the original
    cards_data = [
        {
            "name": "Cash Rewards Card",
            "issuer": "Chase",
            "annual_fee": 0,
            "point_value": 0.01,
            "signup_bonus_value": 200,
            "signup_bonus_min_spend": 1000,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 0,
            "signup_bonus_type": "dollars",
            "reward_categories": [
                {"category": "groceries", "rate": 2.0, "limit": 1500},
                {"category": "gas", "rate": 3.0, "limit": 1500},
                {"category": "dining", "rate": 2.0},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "No foreign transaction fees",
                "0% intro APR for 15 months"
            ]
        },
        {
            "name": "Sapphire Preferred",
            "issuer": "Chase",
            "annual_fee": 95,
            "point_value": 0.0125,
            "signup_bonus_value": 750,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 60000,
            "signup_bonus_type": "points",
            "reward_categories": [
                {"category": "travel", "rate": 2.0},
                {"category": "dining", "rate": 2.0},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "25% more value when you redeem for airfare, hotels, car rentals and cruises through Chase Ultimate Rewards",
                "No foreign transaction fees",
                "$50 annual Ultimate Rewards hotel credit"
            ]
        },
        {
            "name": "Platinum Card",
            "issuer": "American Express",
            "annual_fee": 695,
            "point_value": 0.02,
            "signup_bonus_value": 1500,
            "signup_bonus_min_spend": 6000,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 75000,
            "signup_bonus_type": "points",
            "reward_categories": [
                {"category": "travel", "rate": 5.0},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "$200 annual airline fee credit",
                "$200 annual hotel credit",
                "$189 CLEAR credit",
                "Airport lounge access",
                "Global Entry/TSA PreCheck credit"
            ]
        },
        {
            "name": "Blue Cash Preferred",
            "issuer": "American Express",
            "annual_fee": 95,
            "point_value": 0.01,
            "signup_bonus_value": 300,
            "signup_bonus_min_spend": 3000,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 0,
            "signup_bonus_type": "dollars",
            "reward_categories": [
                {"category": "groceries", "rate": 6.0, "limit": 6000},
                {"category": "streaming", "rate": 6.0, "limit": 6000},
                {"category": "transit", "rate": 3.0},
                {"category": "gas", "rate": 3.0, "limit": 6000},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "0% intro APR for 12 months on purchases and balance transfers"
            ]
        },
        {
            "name": "Venture Rewards",
            "issuer": "Capital One",
            "annual_fee": 95,
            "point_value": 0.01,
            "signup_bonus_value": 750,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 75000,
            "signup_bonus_type": "miles",
            "reward_categories": [
                {"category": "base", "rate": 2.0}
            ],
            "special_offers": [
                "No foreign transaction fees",
                "Transfer partners for enhanced redemption value",
                "$100 Global Entry/TSA PreCheck credit"
            ]
        },
        {
            "name": "Double Cash",
            "issuer": "Citi",
            "annual_fee": 0,
            "point_value": 0.01,
            "signup_bonus_value": 200,
            "signup_bonus_min_spend": 1500,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 0,
            "signup_bonus_type": "dollars",
            "reward_categories": [
                {"category": "base", "rate": 2.0}
            ],
            "special_offers": [
                "1% when you buy, 1% when you pay",
                "0% intro APR for 18 months on balance transfers"
            ]
        },
        {
            "name": "Discover it Cash Back",
            "issuer": "Discover",
            "annual_fee": 0,
            "point_value": 0.01,
            "signup_bonus_value": 0,
            "signup_bonus_min_spend": 0,
            "signup_bonus_time_limit": 0,
            "signup_bonus_points": 0,
            "signup_bonus_type": "cashback_match",
            "reward_categories": [
                {"category": "rotating", "rate": 5.0, "limit": 1500},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "Cashback Match - Discover will match all the cash back you've earned at the end of your first year",
                "0% intro APR for 15 months",
                "No foreign transaction fees"
            ]
        },
        {
            "name": "Custom Cash",
            "issuer": "Citi",
            "annual_fee": 0,
            "point_value": 0.01,
            "signup_bonus_value": 200,
            "signup_bonus_min_spend": 750,
            "signup_bonus_time_limit": 90,
            "signup_bonus_points": 0,
            "signup_bonus_type": "dollars",
            "reward_categories": [
                {"category": "custom", "rate": 5.0, "limit": 500},
                {"category": "base", "rate": 1.0}
            ],
            "special_offers": [
                "5% cash back on up to $500 spent in your top eligible spend category each billing cycle",
                "Categories include gas stations, grocery stores, restaurants, travel, drugstores, and more"
            ]
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for card_data in cards_data:
        # Get the issuer first
        issuer_name = card_data.pop('issuer')
        issuer = CardIssuer.query.filter_by(name=issuer_name).first()
        if not issuer:
            print(f"⚠️  Warning: Issuer '{issuer_name}' not found for card '{card_data['name']}'. Skipping.")
            continue
        
        # Check if card already exists
        existing_card = CreditCard.query.filter_by(
            name=card_data['name'], 
            issuer_id=issuer.id
        ).first()
        
        if existing_card:
            skipped_count += 1
            continue
        
        # Extract reward categories and special offers
        reward_categories = card_data.pop('reward_categories', [])
        special_offers = card_data.pop('special_offers', [])
        
        # Convert lists to JSON strings for database storage
        card_data['reward_categories'] = json.dumps(reward_categories)
        card_data['special_offers'] = json.dumps(special_offers)
        
        # Set the issuer_id
        card_data['issuer_id'] = issuer.id
        
        # Create the card
        card = CreditCard(**card_data)
        db.session.add(card)
        db.session.flush()  # Get the card ID
        
        # Create CreditCardReward relationship records
        for reward_data in reward_categories:
            category_name = reward_data.get('category')
            rate = reward_data.get('rate', 1.0)
            limit = reward_data.get('limit')
            
            if category_name:
                # Find the category by name
                category = Category.get_by_name(category_name)
                if category:
                    # Create the reward relationship
                    credit_card_reward = CreditCardReward(
                        credit_card_id=card.id,
                        category_id=category.id,
                        reward_percent=rate,
                        is_bonus_category=(rate > 1.0),
                        limit=limit
                    )
                    db.session.add(credit_card_reward)
                else:
                    print(f"⚠️  Warning: Category '{category_name}' not found for card '{card.name}'")
        
        created_count += 1
    
    db.session.commit()
    print(f"✅ Seeded {created_count} credit cards (skipped {skipped_count} existing)")
    return created_count

def main():
    """Main function to seed credit cards."""
    app = create_app('development')
    with app.app_context():
        return seed_credit_cards()

if __name__ == "__main__":
    sys.exit(main()) 
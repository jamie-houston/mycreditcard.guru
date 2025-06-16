#!/usr/bin/env python
"""
Seed Credit Cards

This script seeds the database with sample credit cards for development and testing.
Creates example credit cards with different reward structures and features.
Can also import cards from scraped data files in /data/output.
"""

import sys
import os
import json
import glob
from datetime import datetime

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
from app.models import CardIssuer

def seed_credit_cards():
    """Seed the database with sample credit cards."""
    
    # Sample credit cards data based on user specifications
    cards_data = [
        {
            "name": "Sapphire Reserve",
            "issuer": "Chase",
            "annual_fee": 550,
            "reward_type": "points",
            "reward_value_multiplier": 1.5,
            "signup_bonus_points": 60000,
            "signup_bonus_value": 900,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 1.0},
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 3.0}
            ],
            "special_offers": [
                "Premium travel benefits",
                "Airport lounge access",
                "$300 annual travel credit"
            ]
        },
        {
            "name": "Freedom Unlimited",
            "issuer": "Chase",
            "annual_fee": 0,
            "reward_type": "cash_back",
            "reward_value_multiplier": 1,
            "signup_bonus_points": 20000,
            "signup_bonus_value": 200,
            "signup_bonus_min_spend": 500,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 1.0},
                {"category": "dining", "rate": 3.0},
                {"category": "drugstores", "rate": 3.0}
            ],
            "special_offers": [
                "No annual fee",
                "Flat rate cash back"
            ]
        },
        {
            "name": "Ink Business Unlimited",
            "issuer": "Chase",
            "annual_fee": 0,
            "reward_type": "cash_back",
            "reward_value_multiplier": 1,
            "signup_bonus_points": 75000,
            "signup_bonus_value": 750,
            "signup_bonus_min_spend": 6000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 1.5}
            ],
            "special_offers": [
                "Business credit card",
                "No annual fee",
                "Flat rate on all purchases"
            ]
        },
        {
            "name": "Sapphire Preferred",
            "issuer": "Chase",
            "annual_fee": 95,
            "reward_type": "points",
            "reward_value_multiplier": 1.25,
            "signup_bonus_points": 60000,
            "signup_bonus_value": 750,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 1.0},
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 2.0},
                {"category": "streaming", "rate": 3.0}
            ],
            "special_offers": [
                "Transfer partners",
                "No foreign transaction fees",
                "Travel protection"
            ]
        },
        {
            "name": "Platinum",
            "issuer": "American Express",
            "annual_fee": 695,
            "reward_type": "points",
            "reward_value_multiplier": 1.6,
            "signup_bonus_points": 175000,
            "signup_bonus_value": 2800,
            "signup_bonus_min_spend": 8000,
            "signup_bonus_max_months": 6,
            "reward_categories": [
                {"category": "other", "rate": 1.0},
                {"category": "travel", "rate": 5.0}
            ],
            "special_offers": [
                "$200 annual airline fee credit",
                "$200 annual hotel credit",
                "Airport lounge access",
                "Concierge service"
            ]
        },
        {
            "name": "Gold",
            "issuer": "American Express",
            "annual_fee": 325,
            "reward_type": "points",
            "reward_value_multiplier": 1.6,
            "signup_bonus_points": 100000,
            "signup_bonus_value": 1600,
            "signup_bonus_min_spend": 6000,
            "signup_bonus_max_months": 6,
            "reward_categories": [
                {"category": "other", "rate": 1.0},
                {"category": "dining", "rate": 4.0},
                {"category": "travel", "rate": 3.0},
                {"category": "groceries", "rate": 4.0}
            ],
            "special_offers": [
                "$120 annual dining credit",
                "$120 annual Uber credit",
                "No foreign transaction fees"
            ]
        },
        {
            "name": "Travel Rewards credit card for Students",
            "issuer": "Bank of America",
            "annual_fee": 0,
            "reward_type": "points",
            "reward_value_multiplier": 1,
            "signup_bonus_points": 25000,
            "signup_bonus_value": 250,
            "signup_bonus_min_spend": 1000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 1.5},
            ],
            "special_offers": [
                "Earn 3 points per $1 spent on travel purchases booked through the Bank of America Travel Center."
            ]
        },
        {
            "name": "Venture Rewards Credit Card",
            "issuer": "Capital One",
            "annual_fee": 95,
            "reward_type": "miles",
            "reward_value_multiplier": 1,
            "signup_bonus_points": 75000,
            "signup_bonus_value": 750,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "other", "rate": 2},
            ],
            "special_offers": [
                "Earn 5X miles on hotels, vacation rentals and rental cars booked through Capital One Travel."
            ]
        },
        {
            "name": "Strata Premier",
            "issuer": "Citi",
            "annual_fee": 95,
            "reward_type": "points",
            "reward_value_multiplier": 1,
            "signup_bonus_points": 60000,
            "signup_bonus_value": 600,
            "signup_bonus_min_spend": 4000,
            "signup_bonus_max_months": 3,
            "reward_categories": [
                {"category": "travel", "rate": 3},
            ],
            "special_offers": [
                "Earn 5X miles on hotels, vacation rentals and rental cars booked through Capital One Travel."
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

def import_scraped_cards(file_path: str = None) -> int:
    """Import credit cards from scraped data files."""
    
    # Get the flask_app/data/output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_dir = os.path.join(base_dir, 'data', 'output')
    
    if not os.path.exists(output_dir):
        print(f"⚠️  Output directory not found: {output_dir}")
        return 0
    
    # Get all JSON files in output directory, sorted by filename (which includes timestamp)
    if file_path:
        json_files = [file_path] if os.path.exists(file_path) else []
    else:
        json_files = sorted(glob.glob(os.path.join(output_dir, '*.json')))
    
    if not json_files:
        print(f"⚠️  No JSON files found in {output_dir}")
        return 0
    
    total_imported = 0
    
    for json_file in json_files:
        print(f"\n📁 Processing file: {os.path.basename(json_file)}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cards_data = data.get('cards', [])
            if not cards_data:
                print(f"   ⚠️  No cards found in file")
                continue
            
            imported_count = import_cards_from_data(cards_data, os.path.basename(json_file))
            total_imported += imported_count
            print(f"   ✅ Imported {imported_count} cards from {os.path.basename(json_file)}")
            
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(json_file)}: {e}")
            continue
    
    return total_imported


def import_cards_from_data(cards_data: list, source_file: str) -> int:
    """Import cards from a list of card data."""
    created_count = 0
    updated_count = 0
    
    for card_data in cards_data:
        try:
            # Get or create issuer
            issuer_name = card_data.get('issuer', 'Unknown')
            issuer = CardIssuer.query.filter_by(name=issuer_name).first()
            if not issuer:
                # Create new issuer if it doesn't exist
                issuer = CardIssuer(name=issuer_name)
                db.session.add(issuer)
                db.session.flush()
            
            # Check if card already exists
            existing_card = CreditCard.query.filter_by(
                name=card_data.get('name'),
                issuer_id=issuer.id
            ).first()
            
            # Prepare card data for database
            db_card_data = {
                'name': card_data.get('name'),
                'issuer_id': issuer.id,
                'annual_fee': card_data.get('annual_fee', 0.0),
                'reward_type': card_data.get('reward_type', 'points'),
                'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                'signup_bonus_points': card_data.get('signup_bonus_points', 0),
                'signup_bonus_value': card_data.get('signup_bonus_value', 0.0),
                'signup_bonus_min_spend': card_data.get('signup_bonus_min_spend', 0.0),
                'signup_bonus_max_months': card_data.get('signup_bonus_max_months', 3),
                'source': card_data.get('source', 'scraped'),
                'source_url': card_data.get('source_url', ''),
                'import_date': datetime.utcnow()
            }
            
            if existing_card:
                # Update existing card
                for key, value in db_card_data.items():
                    if key != 'import_date':  # Don't update import_date for existing cards
                        setattr(existing_card, key, value)
                card = existing_card
                updated_count += 1
            else:
                # Create new card
                card = CreditCard(**db_card_data)
                db.session.add(card)
                created_count += 1
            
            db.session.flush()  # Get the card ID
            
            # Clear existing reward relationships for this card
            CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
            
            # Create CreditCardReward relationship records
            reward_categories = card_data.get('reward_categories', {})
            if isinstance(reward_categories, dict):
                for category_name, rate in reward_categories.items():
                    # Map category name to database category
                    category = Category.get_by_name(category_name)
                    if category:
                        credit_card_reward = CreditCardReward(
                            credit_card_id=card.id,
                            category_id=category.id,
                            reward_percent=float(rate),
                            is_bonus_category=(float(rate) > 1.0)
                        )
                        db.session.add(credit_card_reward)
                    else:
                        print(f"     ⚠️  Category '{category_name}' not found for card '{card.name}'")
            
        except Exception as e:
            print(f"     ❌ Error importing card '{card_data.get('name', 'Unknown')}': {e}")
            continue
    
    db.session.commit()
    return created_count + updated_count


def main():
    """Main function to seed credit cards."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed credit cards database')
    parser.add_argument('--import-scraped', action='store_true', 
                       help='Import cards from scraped data files in /data/output')
    parser.add_argument('--file', type=str, 
                       help='Import from specific file path')
    parser.add_argument('--sample-only', action='store_true',
                       help='Only seed sample cards (default behavior)')
    
    args = parser.parse_args()
    
    app = create_app('development')
    with app.app_context():
        if args.import_scraped or args.file:
            return import_scraped_cards(args.file)
        else:
            return seed_credit_cards()

if __name__ == "__main__":
    sys.exit(main()) 
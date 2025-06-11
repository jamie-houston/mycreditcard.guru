#!/usr/bin/env python
"""
Comprehensive database seeding script.
This script will:
1. Create all database tables
2. Seed categories
3. Seed sample credit cards
"""

import sys
import os
import json

# Add current directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation

# Default categories commonly used in credit card rewards
DEFAULT_CATEGORIES = [
    {
        'name': 'dining',
        'display_name': 'Dining & Restaurants',
        'description': 'Restaurants, bars, cafes, and food delivery services',
        'icon': 'fas fa-utensils',
        'sort_order': 10,
        'aliases': ['restaurants', 'restaurant', 'dining at restaurants', 'takeout', 'delivery service']
    },
    {
        'name': 'travel',
        'display_name': 'Travel',
        'description': 'Airlines, hotels, rental cars, and travel booking services',
        'icon': 'fas fa-plane',
        'sort_order': 20,
        'aliases': ['travel purchases', 'travel purchased', 'other travel', 'travel booked', 'hotels', 'hotel', 'rental cars', 'car rentals', 'flights', 'airfare', 'attractions']
    },
    {
        'name': 'groceries',
        'display_name': 'Groceries',
        'description': 'Supermarkets and grocery stores',
        'icon': 'fas fa-shopping-cart',
        'sort_order': 30,
        'aliases': ['grocery', 'grocery stores', 'supermarkets', 'online groceries', 'wholesale clubs', 'online grocery']
    },
    {
        'name': 'gas',
        'display_name': 'Gas Stations',
        'description': 'Gas stations and fuel purchases',
        'icon': 'fas fa-gas-pump',
        'sort_order': 40,
        'aliases': ['gas stations', 'gasoline', 'fuel']
    },
    {
        'name': 'entertainment',
        'display_name': 'Entertainment',
        'description': 'Movies, concerts, streaming services, and entertainment venues',
        'icon': 'fas fa-film',
        'sort_order': 50,
        'aliases': []
    },
    {
        'name': 'shopping',
        'display_name': 'Shopping',
        'description': 'Online and retail shopping, department stores',
        'icon': 'fas fa-shopping-bag',
        'sort_order': 60,
        'aliases': ['online retail', 'online purchases']
    },
    {
        'name': 'streaming',
        'display_name': 'Streaming Services',
        'description': 'Video and music streaming subscriptions',
        'icon': 'fas fa-tv',
        'sort_order': 80,
        'aliases': ['streaming services', 'select streaming services', 'streaming subscriptions']
    },
    {
        'name': 'other',
        'display_name': 'Other',
        'description': 'Any expenses that don\'t fit into the above categories',
        'icon': 'fas fa-ellipsis-h',
        'sort_order': 140,
        'aliases': ['all purchases', 'everything else', 'everything', 'all other purchases']
    },
    {
        'name': 'base',
        'display_name': 'Base Rate',
        'description': 'Default rate for all other purchases',
        'icon': 'fas fa-percentage',
        'sort_order': 0,
        'aliases': ['all other purchases']
    }
]

def seed_categories():
    """Create default categories if they don't exist."""
    created_count = 0
    updated_count = 0
    
    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        
        if existing:
            # Update existing category with new data (but keep active status)
            existing.display_name = cat_data['display_name']
            existing.description = cat_data['description']
            existing.icon = cat_data['icon']
            existing.sort_order = cat_data['sort_order']
            existing.set_aliases(cat_data.get('aliases', []))
            updated_count += 1
            print(f"Updated category: {cat_data['display_name']}")
        else:
            # Create new category
            category = Category(
                name=cat_data['name'],
                display_name=cat_data['display_name'],
                description=cat_data['description'],
                icon=cat_data['icon'],
                sort_order=cat_data['sort_order'],
                is_active=True
            )
            category.set_aliases(cat_data.get('aliases', []))
            db.session.add(category)
            created_count += 1
            print(f"Created category: {cat_data['display_name']}")
    
    db.session.commit()
    print(f"\nSeeding completed! Created {created_count} new categories, updated {updated_count} existing categories.")

def seed_credit_cards():
    """Create sample credit cards."""
    # Delete existing cards
    CreditCard.query.delete()
    
    # Create sample credit cards with the new reward system
    cards_data = [
        {
            "card": {
                "name": "Chase Sapphire Preferred® Card",
                "issuer": "Chase",
                "annual_fee": 95,
                "point_value": 0.0125,
                "signup_bonus_value": 600,
                "signup_bonus_min_spend": 4000,
                "signup_bonus_time_limit": 3,
                "signup_bonus_points": 60000,
                "signup_bonus_type": "points",
                "reward_categories": json.dumps([]),  # Empty for new system
                "special_offers": json.dumps([
                    {"type": "25% more value when you redeem for travel through Chase Ultimate Rewards®"},
                    {"type": "Transfer points to airline and hotel partners"}
                ])
            },
            "rewards": [
                ("dining", 3.0),
                ("travel", 2.0),
                ("base", 1.0)
            ]
        },
        {
            "card": {
                "name": "Capital One Venture X Rewards Credit Card",
                "issuer": "Capital One",
                "annual_fee": 395,
                "point_value": 0.01,
                "signup_bonus_value": 750,
                "signup_bonus_min_spend": 4000,
                "signup_bonus_time_limit": 3,
                "signup_bonus_points": 75000,
                "signup_bonus_type": "points",
                "reward_categories": json.dumps([]),
                "special_offers": json.dumps([
                    {"type": "$300 annual travel credit"},
                    {"type": "Priority Pass Select lounge access"},
                    {"type": "TSA PreCheck/Global Entry credit"}
                ])
            },
            "rewards": [
                ("dining", 2.0),
                ("travel", 2.0),
                ("base", 1.0)
            ]
        },
        {
            "card": {
                "name": "American Express Blue Cash Preferred® Card",
                "issuer": "American Express",
                "annual_fee": 95,
                "point_value": 0.01,
                "signup_bonus_value": 250,
                "signup_bonus_min_spend": 3000,
                "signup_bonus_time_limit": 6,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([]),
                "special_offers": json.dumps([
                    {"type": "6% cash back at U.S. supermarkets on up to $6,000 per year"},
                    {"type": "6% cash back on select U.S. streaming subscriptions"}
                ])
            },
            "rewards": [
                ("gas", 3.0),
                ("groceries", 6.0),
                ("streaming", 6.0),
                ("base", 1.0)
            ]
        },
        {
            "card": {
                "name": "Citi Double Cash Card",
                "issuer": "Citi",
                "annual_fee": 0,
                "point_value": 0.01,
                "signup_bonus_value": 200,
                "signup_bonus_min_spend": 1500,
                "signup_bonus_time_limit": 6,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([]),
                "special_offers": json.dumps([
                    {"type": "Earn 1% when you buy, plus 1% as you pay"},
                    {"type": "No annual fee"}
                ])
            },
            "rewards": [
                ("base", 2.0)
            ]
        },
        {
            "card": {
                "name": "Chase Freedom Flex℠",
                "issuer": "Chase",
                "annual_fee": 0,
                "point_value": 0.01,
                "signup_bonus_value": 200,
                "signup_bonus_min_spend": 500,
                "signup_bonus_time_limit": 3,
                "signup_bonus_points": 20000,
                "signup_bonus_type": "points",
                "reward_categories": json.dumps([]),
                "special_offers": json.dumps([
                    {"type": "5% cash back on up to $1,500 in combined purchases in bonus categories each quarter you activate"},
                    {"type": "5% on travel purchased through Chase Ultimate Rewards®"}
                ])
            },
            "rewards": [
                ("dining", 3.0),
                ("travel", 5.0),
                ("base", 1.0)
            ]
        }
    ]
    
    # Add cards to database
    for card_data in cards_data:
        # Create the card
        card = CreditCard(**card_data["card"])
        db.session.add(card)
        db.session.flush()  # Get the card ID
        
        # Add reward categories
        for category_name, reward_rate in card_data["rewards"]:
            card.add_reward_category(category_name, reward_rate)
    
    db.session.commit()
    print(f"Added {len(cards_data)} credit cards to the database.")

def main():
    """Main seeding function."""
    print("🚀 Starting comprehensive database seeding...")
    
    app = create_app()
    with app.app_context():
        print("\n1️⃣ Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        print("\n2️⃣ Seeding categories...")
        seed_categories()
        
        print("\n3️⃣ Seeding credit cards...")
        seed_credit_cards()
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nYou can now run the Flask app with:")
        print("  python run.py")

if __name__ == "__main__":
    main() 
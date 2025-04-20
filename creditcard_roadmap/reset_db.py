#!/usr/bin/env python
"""
Reset and initialize the database with the current models.
This bypasses migrations and directly creates tables from the models.
"""

import sys
from app import create_app, db
from app.models.credit_card import CreditCard

def main():
    """Reset and initialize the database."""
    print("Initializing database...")
    
    # Create app context
    app = create_app('default')
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("Dropped all existing tables.")
        
        # Create all tables based on current models
        db.create_all()
        print("Created all tables from models.")
        
        # Initialize with sample data if needed
        # add_sample_data()
        
        print("Database initialization complete!")
    
    return 0

def add_sample_data():
    """Add sample credit cards to the database."""
    from datetime import datetime
    import json
    
    # Sample credit cards
    cards = [
        {
            "name": "Chase Sapphire Preferred",
            "issuer": "Chase",
            "annual_fee": 95.0,
            "signup_bonus_points": 60000,
            "signup_bonus_value": 750.0,
            "signup_bonus_min_spend": 4000.0,
            "signup_bonus_time_limit": 3,
            "reward_categories": json.dumps([
                {"category": "dining", "percentage": 3},
                {"category": "travel", "percentage": 2},
                {"category": "other", "percentage": 1}
            ]),
            "special_offers": json.dumps([
                {"type": "travel_credit", "amount": 50, "frequency": "annual"}
            ]),
            "source": "sample",
            "source_url": "Sample Data",
            "import_date": datetime.utcnow()
        },
        {
            "name": "Capital One Venture",
            "issuer": "Capital One",
            "annual_fee": 95.0,
            "signup_bonus_points": 75000,
            "signup_bonus_value": 750.0,
            "signup_bonus_min_spend": 4000.0,
            "signup_bonus_time_limit": 3,
            "reward_categories": json.dumps([
                {"category": "travel", "percentage": 2},
                {"category": "other", "percentage": 1}
            ]),
            "special_offers": json.dumps([]),
            "source": "sample",
            "source_url": "Sample Data",
            "import_date": datetime.utcnow()
        }
    ]
    
    # Add cards to database
    for card_data in cards:
        card = CreditCard(**card_data)
        db.session.add(card)
    
    db.session.commit()
    print(f"Added {len(cards)} sample credit cards.")

if __name__ == "__main__":
    sys.exit(main()) 
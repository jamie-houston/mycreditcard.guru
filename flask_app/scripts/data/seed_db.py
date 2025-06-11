#!/usr/bin/env python
"""
Database Seeder

This script seeds the database with sample credit cards for development and testing.
Creates 5 example credit cards with different reward structures and features.
"""

from app import create_app, db
from app.models.credit_card import CreditCard
import json

def seed_credit_cards():
    app = create_app()
    with app.app_context():
        # Delete existing cards
        CreditCard.query.delete()
        
        # Create sample credit cards
        cards = [
            {
                "name": "Cash Rewards Card",
                "issuer": "Example Bank",
                "annual_fee": 0,
                "point_value": 0.01,
                "signup_bonus_value": 200,
                "signup_bonus_min_spend": 1000,
                "signup_bonus_time_limit": 90,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([
                    {"category": "groceries", "rate": 2.0},
                    {"category": "gas", "rate": 3.0},
                    {"category": "dining", "rate": 2.0},
                    {"category": "base", "rate": 1.0}
                ]),
                "special_offers": json.dumps([
                    {"type": "No foreign transaction fees"}
                ])
            },
            {
                "name": "Premium Travel Card",
                "issuer": "Luxury Bank",
                "annual_fee": 95,
                "point_value": 0.015,
                "signup_bonus_value": 600,
                "signup_bonus_min_spend": 3000,
                "signup_bonus_time_limit": 90,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([
                    {"category": "travel", "rate": 3.0},
                    {"category": "dining", "rate": 3.0},
                    {"category": "entertainment", "rate": 2.0},
                    {"category": "base", "rate": 1.0}
                ]),
                "special_offers": json.dumps([
                    {"type": "Airport lounge access"},
                    {"type": "Global Entry credit"}
                ])
            },
            {
                "name": "Simple Cash Back",
                "issuer": "Basic Bank",
                "annual_fee": 0,
                "point_value": 0.01,
                "signup_bonus_value": 150,
                "signup_bonus_min_spend": 500,
                "signup_bonus_time_limit": 90,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([
                    {"category": "base", "rate": 1.5}
                ]),
                "special_offers": json.dumps([])
            },
            {
                "name": "Grocery Plus",
                "issuer": "Food Bank",
                "annual_fee": 0,
                "point_value": 0.01,
                "signup_bonus_value": 200,
                "signup_bonus_min_spend": 1000,
                "signup_bonus_time_limit": 90,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([
                    {"category": "groceries", "rate": 5.0},
                    {"category": "base", "rate": 1.0}
                ]),
                "special_offers": json.dumps([
                    {"type": "Special supermarket discounts"}
                ])
            },
            {
                "name": "Ultra Premium Card",
                "issuer": "Elite Bank",
                "annual_fee": 550,
                "point_value": 0.02,
                "signup_bonus_value": 1000,
                "signup_bonus_min_spend": 5000,
                "signup_bonus_time_limit": 90,
                "signup_bonus_points": 0,
                "signup_bonus_type": "dollars",
                "reward_categories": json.dumps([
                    {"category": "travel", "rate": 5.0},
                    {"category": "dining", "rate": 3.0},
                    {"category": "entertainment", "rate": 3.0},
                    {"category": "base", "rate": 1.5}
                ]),
                "special_offers": json.dumps([
                    {"type": "Annual travel credit $300"},
                    {"type": "Airport lounge access"},
                    {"type": "Hotel status upgrade"}
                ])
            }
        ]
        
        # Add cards to database
        for card_data in cards:
            card = CreditCard(**card_data)
            db.session.add(card)
        
        db.session.commit()
        print(f"Added {len(cards)} credit cards to the database.")

if __name__ == "__main__":
    seed_credit_cards() 
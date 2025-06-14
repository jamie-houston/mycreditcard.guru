#!/usr/bin/env python
"""
Seed User Profiles

This script seeds the database with sample user profiles for development and testing.
Creates example profiles with different spending patterns and preferences.
"""

import sys
import os
import json

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models.user_profile import UserProfile
from app.models.category import Category

def seed_profiles():
    """Seed the database with sample user profiles."""
    
    # Sample user profiles data
    profiles_data = [
        {
            "session_id": "demo_user_1",
            "credit_score": 750,
            "annual_income": 75000,
            "monthly_spending": 3500,
            "spending_categories": {
                "dining": 800,
                "groceries": 600,
                "gas": 300,
                "travel": 400,
                "entertainment": 200,
                "shopping": 500,
                "other": 700
            },
            "preferences": {
                "max_annual_fee": 95,
                "preferred_rewards": ["cash_back", "travel_points"],
                "signup_bonus_importance": "high",
                "foreign_transaction_fees": "avoid"
            },
            "constraints": {
                "min_credit_score": 700,
                "max_annual_fee": 100,
                "avoid_categories": []
            }
        },
        {
            "session_id": "demo_user_2", 
            "credit_score": 680,
            "annual_income": 55000,
            "monthly_spending": 2800,
            "spending_categories": {
                "groceries": 700,
                "gas": 400,
                "dining": 300,
                "utilities": 250,
                "entertainment": 150,
                "shopping": 400,
                "other": 600
            },
            "preferences": {
                "max_annual_fee": 0,
                "preferred_rewards": ["cash_back"],
                "signup_bonus_importance": "medium",
                "foreign_transaction_fees": "avoid"
            },
            "constraints": {
                "min_credit_score": 650,
                "max_annual_fee": 0,
                "avoid_categories": ["travel"]
            }
        },
        {
            "session_id": "demo_user_3",
            "credit_score": 800,
            "annual_income": 120000,
            "monthly_spending": 5500,
            "spending_categories": {
                "travel": 1200,
                "dining": 900,
                "groceries": 500,
                "entertainment": 400,
                "shopping": 800,
                "gas": 200,
                "other": 1500
            },
            "preferences": {
                "max_annual_fee": 550,
                "preferred_rewards": ["travel_points", "airline_miles"],
                "signup_bonus_importance": "very_high",
                "foreign_transaction_fees": "avoid"
            },
            "constraints": {
                "min_credit_score": 750,
                "max_annual_fee": 600,
                "avoid_categories": []
            }
        },
        {
            "session_id": "demo_user_4",
            "credit_score": 720,
            "annual_income": 85000,
            "monthly_spending": 4200,
            "spending_categories": {
                "groceries": 800,
                "dining": 600,
                "gas": 350,
                "streaming": 50,
                "shopping": 700,
                "home_improvement": 400,
                "other": 1300
            },
            "preferences": {
                "max_annual_fee": 200,
                "preferred_rewards": ["cash_back", "flexible_points"],
                "signup_bonus_importance": "high",
                "foreign_transaction_fees": "ok"
            },
            "constraints": {
                "min_credit_score": 700,
                "max_annual_fee": 250,
                "avoid_categories": ["travel"]
            }
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for profile_data in profiles_data:
        # Check if profile already exists
        existing_profile = UserProfile.query.filter_by(
            session_id=profile_data['session_id']
        ).first()
        
        if existing_profile:
            skipped_count += 1
            continue
        
        # Convert dictionaries to JSON strings for database storage
        spending_categories_json = json.dumps(profile_data['spending_categories'])
        preferences_json = json.dumps(profile_data['preferences'])
        constraints_json = json.dumps(profile_data['constraints'])
        
        # Create the profile
        profile = UserProfile(
            session_id=profile_data['session_id'],
            credit_score=profile_data['credit_score'],
            annual_income=profile_data['annual_income'],
            monthly_spending=profile_data['monthly_spending'],
            spending_categories=spending_categories_json,
            preferences=preferences_json,
            constraints=constraints_json
        )
        
        db.session.add(profile)
        created_count += 1
    
    db.session.commit()
    print(f"✅ Seeded {created_count} user profiles (skipped {skipped_count} existing)")
    return created_count

def main():
    """Main function to seed user profiles."""
    app = create_app('development')
    with app.app_context():
        return seed_profiles()

if __name__ == "__main__":
    sys.exit(main()) 
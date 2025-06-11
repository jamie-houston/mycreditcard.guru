#!/usr/bin/env python
"""
User Profile Validator

This script checks all user profiles in the database and displays their spending
patterns and reward preferences for debugging and validation purposes.
"""

from app import create_app, db
from app.models.user_data import UserProfile
import json

def check_profiles():
    app = create_app()
    with app.app_context():
        profiles = UserProfile.query.all()
        print(f"Total profiles: {len(profiles)}")
        
        for profile in profiles:
            print(f"\nProfile ID: {profile.id}")
            print(f"Name: {profile.name}")
            print(f"User ID: {profile.user_id}")
            print(f"Session ID: {profile.session_id}")
            print(f"Credit Score: {profile.credit_score}")
            print(f"Income: ${profile.income}")
            print(f"Total Monthly Spend: ${profile.total_monthly_spend}")
            
            try:
                category_spending = json.loads(profile.category_spending)
                print(f"Category Spending: {category_spending}")
                print(f"Categories: {len(category_spending.keys())}")
                print(f"Total from categories: ${sum(category_spending.values())}")
            except:
                print("Error parsing category spending")
                
            try:
                reward_preferences = json.loads(profile.reward_preferences)
                print(f"Reward Preferences: {reward_preferences}")
            except:
                print("Error parsing reward preferences")

if __name__ == "__main__":
    check_profiles() 
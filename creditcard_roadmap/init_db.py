#!/usr/bin/env python
import os
from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.profile import CreditCardProfile
from app.models.credit_card import CreditCard
from app.models.category import Category
from app.models.goal import Goal
import random
import json

# Function to generate random profile data
def generate_random_profile(user_id):
    # Generate random total monthly spending between 5000 and 10000
    total_monthly_spend = round(random.uniform(5000, 10000), 2)
    
    # Generate income as 15 times the total spending
    income = round(total_monthly_spend * 15, 2)
    
    # Generate random credit score between 500 and 800
    credit_score = random.randint(500, 800)
    
    # List of spending categories
    categories = [
        'groceries', 'dining', 'gas', 'travel', 'entertainment', 
        'shopping', 'utilities', 'healthcare', 'transportation', 'other'
    ]
    
    # Generate random spending by category that adds up to total_monthly_spend
    category_spending = {}
    
    # First, assign a random percentage to each category
    percentages = [random.random() for _ in range(len(categories))]
    total_percentage = sum(percentages)
    
    # Normalize percentages to sum to 1
    percentages = [p / total_percentage for p in percentages]
    
    # Calculate spending amount for each category
    for i, category in enumerate(categories):
        amount = round(percentages[i] * total_monthly_spend, 2)
        if amount > 0:
            category_spending[category] = amount
    
    # Ensure the total matches exactly by adjusting the "other" category
    current_total = sum(category_spending.values())
    adjustment = total_monthly_spend - current_total
    
    if 'other' in category_spending:
        category_spending['other'] += adjustment
    else:
        category_spending['other'] = adjustment
    
    # Round all values to 2 decimal places
    category_spending = {k: round(v, 2) for k, v in category_spending.items()}
    
    # Reward preferences
    reward_options = [
        'cash_back', 'travel_points', 'airline_miles', 'hotel_points', 
        'statement_credits', 'shopping_benefits'
    ]
    
    # Randomly select 1 or 2 reward preferences
    num_preferences = random.randint(1, 2)
    reward_preferences = random.sample(reward_options, num_preferences)
    
    # Create a name for the profile
    profile_name = f"Default Spending Profile ({total_monthly_spend:.0f}/mo)"
    
    return UserProfile(
        user_id=user_id,
        name=profile_name,
        credit_score=credit_score,
        income=income,
        total_monthly_spend=total_monthly_spend,
        category_spending=json.dumps(category_spending),
        reward_preferences=json.dumps(reward_preferences)
    )

def init_db():
    # Create a Flask app with the appropriate config
    app = create_app(os.getenv('FLASK_CONFIG') or 'development')

    # Push an application context to make the app aware of the db operations
    with app.app_context():
        # Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating all tables...")
        db.create_all()
        
        # Create an admin user
        print("Creating admin user...")
        admin = User(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_admin=True
        )
        
        # Create demo user
        print("Creating demo user...")
        demo = User(
            username='demo',
            email='demo@demo.com',
            password='test1234',
            is_admin=False
        )
        
        db.session.add(admin)
        db.session.add(demo)
        db.session.commit()
        
        # Create random spending profile for demo user
        print("Creating random spending profile for demo user...")
        profile = generate_random_profile(demo.id)
        db.session.add(profile)
        db.session.commit()
        
        print("Database initialization completed successfully!")
        print(f"Admin user created. Username: admin, Password: admin123")
        print(f"Demo user created. Username: demo, Email: demo@demo.com, Password: test1234")
        print(f"Demo user profile created with:")
        print(f"  - Monthly spending: ${profile.total_monthly_spend:.2f}")
        print(f"  - Income: ${profile.income:.2f}")
        print(f"  - Credit score: {profile.credit_score}")
        print(f"  - Categories: {profile.category_spending}")
        print(f"  - Reward preferences: {profile.reward_preferences}")

if __name__ == '__main__':
    init_db() 
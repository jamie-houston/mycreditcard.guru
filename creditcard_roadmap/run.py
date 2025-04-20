from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from datetime import datetime
import os
import sqlite3
from pathlib import Path
import random
import json

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

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

# Check if database exists and initialize if needed
def init_database():
    # Check if database exists
    db_path = Path("app.db")
    db_exists = db_path.exists()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if users table is empty
        user_count = User.query.count()
        if user_count == 0:
            print("Creating default users...")
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password='admin123',
                is_admin=True
            )
            
            # Create demo user
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
            
            print(f"Demo user profile created with:")
            print(f"  - Monthly spending: ${profile.total_monthly_spend:.2f}")
            print(f"  - Income: ${profile.income:.2f}")
            print(f"  - Credit score: {profile.credit_score}")
            print(f"  - Categories: {profile.category_spending}")
            print(f"  - Reward preferences: {profile.reward_preferences}")
            
            print("Default users created")

# Initialize database when app starts
init_database()

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db)

# Add a health check route to test if the app is working
@app.route('/health')
def health_check():
    return {'status': 'ok', 'db_status': 'connected', 'time': str(datetime.utcnow())}

if __name__ == '__main__':
    app.run(debug=True) 
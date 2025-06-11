from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
import json
import uuid

def create_test_profile():
    app = create_app()
    with app.app_context():
        # Find the test user
        user = User.query.filter_by(email='user@example.com').first()
        
        if not user:
            print("Test user not found. Please run create_test_user.py first.")
            return
            
        # Check if user already has a profile
        existing_profile = UserProfile.query.filter_by(user_id=user.id).first()
        
        if existing_profile:
            print(f"User already has a profile: {existing_profile.name}")
            
            # Update the existing profile with sample data
            existing_profile.name = "Sample Spending Profile"
            existing_profile.credit_score = 750
            existing_profile.income = 75000
            
            # Set sample spending data
            category_spending = {
                "groceries": 500,
                "dining": 300,
                "gas": 200,
                "travel": 250,
                "entertainment": 150,
                "shopping": 300,
                "utilities": 250,
                "healthcare": 100,
                "transportation": 150,
                "other": 300
            }
            
            existing_profile.total_monthly_spend = sum(category_spending.values())
            existing_profile.category_spending = json.dumps(category_spending)
            
            # Set reward preferences
            reward_preferences = ["cash_back", "travel_points", "dining"]
            existing_profile.reward_preferences = json.dumps(reward_preferences)
            
            # Set constraints
            existing_profile.max_cards = 3
            existing_profile.max_annual_fees = 200
            
            db.session.commit()
            print("Updated existing user profile with sample data.")
        else:
            # Create a new profile
            new_profile = UserProfile(
                user_id=user.id,
                name="Sample Spending Profile",
                credit_score=750,
                income=75000
            )
            
            # Set sample spending data
            category_spending = {
                "groceries": 500,
                "dining": 300,
                "gas": 200,
                "travel": 250,
                "entertainment": 150,
                "shopping": 300,
                "utilities": 250,
                "healthcare": 100,
                "transportation": 150,
                "other": 300
            }
            
            new_profile.total_monthly_spend = sum(category_spending.values())
            new_profile.category_spending = json.dumps(category_spending)
            
            # Set reward preferences
            reward_preferences = ["cash_back", "travel_points", "dining"]
            new_profile.reward_preferences = json.dumps(reward_preferences)
            
            # Set constraints
            new_profile.max_cards = 3
            new_profile.max_annual_fees = 200
            
            db.session.add(new_profile)
            db.session.commit()
            print("Created new user profile with sample data.")
            
        # Now create a profile for anonymous users
        session_id = str(uuid.uuid4())
        anon_profile = UserProfile(
            session_id=session_id,
            name="Anonymous Profile",
            credit_score=700,
            income=60000
        )
        
        # Set sample spending data for anonymous user
        anon_spending = {
            "groceries": 400,
            "dining": 200,
            "gas": 150,
            "travel": 100,
            "entertainment": 100,
            "shopping": 200,
            "utilities": 200,
            "other": 250
        }
        
        anon_profile.total_monthly_spend = sum(anon_spending.values())
        anon_profile.category_spending = json.dumps(anon_spending)
        anon_profile.reward_preferences = json.dumps(["cash_back", "shopping_benefits"])
        anon_profile.max_cards = 2
        anon_profile.max_annual_fees = 100
        
        db.session.add(anon_profile)
        db.session.commit()
        print(f"Created anonymous profile with session_id: {session_id}")
        
        print("\nTest profiles created successfully!")
        print(f"User profile total spend: ${sum(category_spending.values())}")
        print(f"Anonymous profile total spend: ${sum(anon_spending.values())}")

if __name__ == "__main__":
    create_test_profile() 
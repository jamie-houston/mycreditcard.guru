#!/usr/bin/env python
"""
Test Data Creator

This script creates comprehensive test data including users, profiles, credit cards,
and recommendations for development and testing purposes. Creates admin, example,
and test users with realistic spending patterns and card recommendations.
"""

from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
import json
from datetime import datetime

def create_test_data():
    """Create test user and profile."""
    app = create_app('development')
    with app.app_context():
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='adminpass',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created admin user with email: {admin_user.email}")
            
        # Create example user if it doesn't exist
        example_user = User.query.filter_by(email='example@example.com').first()
        if not example_user:
            example_user = User(
                username='example',
                email='example@example.com',
                password='examplepass',
                is_admin=False
            )
            db.session.add(example_user)
            db.session.commit()
            print(f"Created example user with email: {example_user.email}")
        
        # Create test user if it doesn't exist
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(
                username='test_user',
                email='test@example.com',
                password='password123'
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created test user with email: {user.email}")
        
        # Create profile for admin
        admin_profile = UserProfile.query.filter_by(user_id=admin_user.id).first()
        if not admin_profile:
            admin_profile = UserProfile(
                user_id=admin_user.id,
                name='Admin Profile',
                credit_score=800,
                income=150000.0,
                total_monthly_spend=8000.0,
                category_spending=json.dumps({
                    "dining": 1000,
                    "travel": 2000,
                    "groceries": 800,
                    "gas": 300,
                    "entertainment": 500,
                    "other": 3400
                })
            )
            db.session.add(admin_profile)
            db.session.commit()
            print(f"Created profile for admin user")
        
        # Create profile for example user
        example_profile = UserProfile.query.filter_by(user_id=example_user.id).first()
        if not example_profile:
            example_profile = UserProfile(
                user_id=example_user.id,
                name='Example Profile',
                credit_score=720,
                income=75000.0,
                total_monthly_spend=3500.0,
                category_spending=json.dumps({
                    "dining": 400,
                    "travel": 500,
                    "groceries": 600,
                    "gas": 250,
                    "entertainment": 200,
                    "other": 1550
                })
            )
            db.session.add(example_profile)
            db.session.commit()
            print(f"Created profile for example user")
        
        # Create test profile if it doesn't exist
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = UserProfile(
                user_id=user.id,
                name='Test Profile',
                credit_score=750,
                income=100000.0,
                total_monthly_spend=5000.0,
                category_spending=json.dumps({
                    "dining": 500,
                    "travel": 1000,
                    "groceries": 800,
                    "gas": 200,
                    "entertainment": 300,
                    "other": 2200
                })
            )
            db.session.add(profile)
            db.session.commit()
            print(f"Created test profile for user: {user.email}")
        
        # Create a test credit card if it doesn't exist
        card = CreditCard.query.filter_by(name='Test Travel Card').first()
        if not card:
            card = CreditCard(
                name='Test Travel Card',
                issuer='Test Bank',
                annual_fee=95.0,
                point_value=0.01,
                is_active=True,
                signup_bonus_points=60000,
                signup_bonus_value=600.0,
                signup_bonus_min_spend=4000.0,
                signup_bonus_time_limit=3,
                reward_categories=json.dumps([
                    {"category": "travel", "rate": 3.0},
                    {"category": "dining", "rate": 2.0},
                    {"category": "groceries", "rate": 1.5},
                    {"category": "gas", "rate": 1.0},
                    {"category": "entertainment", "rate": 1.0},
                    {"category": "other", "rate": 1.0}
                ]),
                special_offers=json.dumps([{"type": "travel_credit", "amount": 100}])
            )
            db.session.add(card)
            db.session.commit()
            print(f"Created test credit card: {card.name}")
            
        # Create a cash back credit card if it doesn't exist
        cash_card = CreditCard.query.filter_by(name='Cash Back Card').first()
        if not cash_card:
            cash_card = CreditCard(
                name='Cash Back Card',
                issuer='Cash Bank',
                annual_fee=0.0,
                point_value=0.01,
                is_active=True,
                signup_bonus_points=20000,
                signup_bonus_value=200.0,
                signup_bonus_min_spend=1000.0,
                signup_bonus_time_limit=3,
                signup_bonus_type='points',
                reward_categories=json.dumps([
                    {"category": "groceries", "rate": 3.0},
                    {"category": "gas", "rate": 3.0},
                    {"category": "dining", "rate": 1.0},
                    {"category": "travel", "rate": 1.0},
                    {"category": "entertainment", "rate": 1.0},
                    {"category": "other", "rate": 1.5}
                ]),
                special_offers=json.dumps([{"type": "cash_bonus", "amount": 50}])
            )
            db.session.add(cash_card)
            db.session.commit()
            print(f"Created cash back credit card: {cash_card.name}")
        
        # Create a test recommendation if it doesn't exist
        recommendation = Recommendation.query.filter_by(user_id=user.id, user_profile_id=profile.id).first()
        if not recommendation:
            recommendation = Recommendation(
                user_id=user.id,
                user_profile_id=profile.id,
                created_at=datetime.utcnow(),
                _spending_profile=profile.category_spending,
                _card_preferences='{}',
                _recommended_sequence='[1]',
                _card_details='{"1": {"annual_value": 500, "net_value": 405}}',
                total_value=500.0,
                total_annual_fees=95.0,
                _per_month_value='[41.67, 83.33, 125.0, 166.67, 208.33, 250.0, 291.67, 333.33, 375.0, 416.67, 458.33, 500.0]',
                card_count=1
            )
            db.session.add(recommendation)
            db.session.commit()
            print(f"Created test recommendation for profile: {profile.id}")
            
        # Create a recommendation for example user
        example_rec = Recommendation.query.filter_by(user_id=example_user.id, user_profile_id=example_profile.id).first()
        if not example_rec:
            example_rec = Recommendation(
                user_id=example_user.id,
                user_profile_id=example_profile.id,
                created_at=datetime.utcnow(),
                _spending_profile=example_profile.category_spending,
                _card_preferences='{}',
                _recommended_sequence='[2]',
                _card_details='{"2": {"annual_value": 300, "net_value": 300}}',
                total_value=300.0,
                total_annual_fees=0.0,
                _per_month_value='[25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0, 275.0, 300.0]',
                card_count=1
            )
            db.session.add(example_rec)
            db.session.commit()
            print(f"Created recommendation for example user")
        
        print("\nAvailable User Credentials:")
        print("Admin User:")
        print("  Email: admin@example.com")
        print("  Password: adminpass")
        print("\nExample User:")
        print("  Email: example@example.com")
        print("  Password: examplepass")
        print("\nTest User:")
        print("  Email: test@example.com")
        print("  Password: password123")
        print("\nImportant URLs:")
        print("Login: http://127.0.0.1:5000/login")
        print("List Recommendations: http://127.0.0.1:5000/recommendations/list")
        print(f"View Recommendation: http://127.0.0.1:5000/recommendations/view/{recommendation.id if recommendation else '1'}")

if __name__ == '__main__':
    create_test_data() 
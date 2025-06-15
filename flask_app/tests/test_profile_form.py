"""
Test profile form functionality.

This module tests the user profile form, including:
- Profile creation without basic information fields (credit_score, income, name)
- Default value handling
- Category spending processing
- Reward type and constraint handling
"""

import pytest
import json
from app import create_app, db
from app.models.user_data import UserProfile


@pytest.fixture(scope="module")
def test_app():
    """Create a test Flask application."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return test_app.test_client()


class TestProfileForm:
    """Test profile form functionality."""

    def test_profile_creation_with_defaults(self, test_app):
        """Test that profiles can be created with default values for removed fields."""
        with test_app.app_context():
            # Create a profile with default values for removed fields
            profile = UserProfile(
                name='Test Profile',  # Default name
                credit_score=750,     # Default credit score  
                income=75000,         # Default income
                total_monthly_spend=2000,
                category_spending=json.dumps({
                    'dining': 500,
                    'travel': 300,
                    'groceries': 400,
                    'other': 800
                }),
                reward_type='points',
                max_cards=2,
                max_annual_fees=500,
                session_id='test-session-defaults'
            )
            
            db.session.add(profile)
            db.session.commit()
            
            # Verify the profile was created correctly
            saved_profile = UserProfile.query.filter_by(session_id='test-session-defaults').first()
            assert saved_profile is not None
            assert saved_profile.name == 'Test Profile'
            assert saved_profile.credit_score == 750
            assert saved_profile.income == 75000
            assert saved_profile.reward_type == 'points'
            assert saved_profile.max_cards == 2
            assert saved_profile.max_annual_fees == 500
            
            spending = saved_profile.get_category_spending()
            assert spending['dining'] == 500
            assert spending['travel'] == 300
            assert spending['groceries'] == 400
            assert spending['other'] == 800
            
            # Clean up
            db.session.delete(saved_profile)
            db.session.commit()

    def test_profile_different_reward_types(self, test_app):
        """Test profile creation with different reward types."""
        reward_types = ['points', 'cash_back', 'miles', 'hotel']
        
        with test_app.app_context():
            for i, reward_type in enumerate(reward_types):
                profile = UserProfile(
                    name=f'Test Profile {reward_type}',
                    credit_score=750,
                    income=75000,
                    total_monthly_spend=1000,
                    category_spending=json.dumps({'dining': 500, 'other': 500}),
                    reward_type=reward_type,
                    max_cards=1,
                    session_id=f'test-session-{reward_type}'
                )
                
                db.session.add(profile)
                db.session.commit()
                
                # Verify the reward type was set correctly
                saved_profile = UserProfile.query.filter_by(session_id=f'test-session-{reward_type}').first()
                assert saved_profile is not None
                assert saved_profile.reward_type == reward_type
                assert saved_profile.get_reward_type() == reward_type
                
                # Clean up
                db.session.delete(saved_profile)
                db.session.commit()

    def test_profile_constraints_handling(self, test_app):
        """Test that profile constraints are handled correctly."""
        with test_app.app_context():
            # Test with various constraint combinations
            test_cases = [
                {
                    'max_cards': 1,
                    'max_annual_fees': 0,  # No annual fees
                },
                {
                    'max_cards': 3,
                    'max_annual_fees': 500,
                },
                {
                    'max_cards': 2,
                    'max_annual_fees': 1000,  # High limit instead of None
                }
            ]
            
            for i, constraints in enumerate(test_cases):
                profile = UserProfile(
                    name=f'Test Constraints {i}',
                    credit_score=750,
                    income=75000,
                    total_monthly_spend=1500,
                    category_spending=json.dumps({'dining': 800, 'other': 700}),
                    reward_type='points',
                    session_id=f'test-constraints-{i}',
                    preferred_issuer_id=None,
                    **constraints
                )
                
                db.session.add(profile)
                db.session.commit()
                
                # Verify constraints were set correctly
                saved_profile = UserProfile.query.filter_by(session_id=f'test-constraints-{i}').first()
                assert saved_profile is not None
                assert saved_profile.max_cards == constraints['max_cards']
                assert saved_profile.max_annual_fees == constraints['max_annual_fees']
                assert saved_profile.preferred_issuer_id is None
                
                # Clean up
                db.session.delete(saved_profile)
                db.session.commit()

    def test_category_spending_processing(self, test_app):
        """Test that category spending is processed correctly."""
        with test_app.app_context():
            spending_data = {
                'dining': 600,
                'travel': 400,
                'groceries': 500,
                'gas': 200,
                'entertainment': 150,
                'other': 250
            }
            
            profile = UserProfile(
                name='Test Spending',
                credit_score=750,
                income=75000,
                total_monthly_spend=sum(spending_data.values()),
                category_spending=json.dumps(spending_data),
                reward_type='points',
                max_cards=2,
                session_id='test-spending'
            )
            
            db.session.add(profile)
            db.session.commit()
            
            # Verify spending data was stored and can be retrieved correctly
            saved_profile = UserProfile.query.filter_by(session_id='test-spending').first()
            assert saved_profile is not None
            
            retrieved_spending = saved_profile.get_category_spending()
            assert retrieved_spending == spending_data
            
            # Test total spend calculation
            calculated_total = saved_profile.calculate_total_spend()
            assert calculated_total == sum(spending_data.values())
            assert calculated_total == saved_profile.total_monthly_spend
            
            # Clean up
            db.session.delete(saved_profile)
            db.session.commit()

    def test_profile_form_get_request(self, client, test_app):
        """Test that the profile form loads correctly via GET request."""
        with test_app.app_context():
            response = client.get('/profile')
            assert response.status_code == 200
            
            # Check that the form contains expected elements
            html = response.data.decode('utf-8')
            assert 'Monthly Spending by Category' in html
            assert 'Constraints' in html
            assert 'Generate Recommendations' in html
            assert 'csrf_token' in html  # CSRF token should be present
            
            # Check that basic information section is NOT present
            assert 'Basic Information' not in html
            assert 'Credit Score' not in html
            assert 'Annual Income' not in html
            assert 'Profile Name' not in html 
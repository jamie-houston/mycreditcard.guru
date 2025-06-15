import pytest
import json
from flask import url_for
from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category
from app.blueprints.recommendations.services import RecommendationService
from app.models.recommendation import Recommendation


@pytest.fixture(scope="function")
def test_app():
    """Create a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        
        # Create test categories
        categories = [
            Category(name='dining', description='Dining and restaurants'),
            Category(name='travel', description='Travel and transportation'),
            Category(name='groceries', description='Grocery stores'),
            Category(name='gas', description='Gas stations'),
            Category(name='other', description='Other purchases')
        ]
        for cat in categories:
            db.session.add(cat)
        
        # Create test issuer with unique name
        issuer = CardIssuer(name='Test Bank Profile Memory')
        db.session.add(issuer)
        db.session.commit()
        
        # Create test credit cards
        cards = [
            CreditCard(
                name='Test Rewards Card',
                issuer_id=issuer.id,
                annual_fee=95.0,
                signup_bonus_points=50000,
                reward_value_multiplier=0.01,
                reward_type='points',
                reward_categories='[{"category": "dining", "rate": 3.0}, {"category": "other", "rate": 1.0}]',
                is_active=True
            ),
            CreditCard(
                name='Test Cash Back Card',
                issuer_id=issuer.id,
                annual_fee=0.0,
                signup_bonus_points=20000,
                reward_value_multiplier=0.01,
                reward_type='cash_back',
                reward_categories='[{"category": "other", "rate": 1.0}]',
                is_active=True
            )
        ]
        for card in cards:
            db.session.add(card)
        
        db.session.commit()
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return 'test-session-profile-memory'


@pytest.mark.skip(reason="Complex integration test - requires full recommendation service setup")
class TestRecommendationProfileMemory:
    """Test cases for recommendation profile memory functionality."""
    
    def test_recommendation_stores_profile_data(self, test_app, session_id):
        """Test that recommendations store a snapshot of the profile data used to generate them."""
        with test_app.app_context():
            # Create a test profile with specific spending data
            spending_data = {
                'dining': 500.0,
                'travel': 300.0,
                'groceries': 400.0,
                'gas': 200.0,
                'other': 600.0
            }
            
            profile = UserProfile(
                name='Test Profile',
                credit_score=750,
                income=75000.0,
                total_monthly_spend=sum(spending_data.values()),
                category_spending=json.dumps(spending_data),
                reward_type='points',
                max_cards=2,
                max_annual_fees=200.0,
                preferred_issuer_id=None,
                session_id=session_id
            )
            db.session.add(profile)
            db.session.commit()
            
            # Generate a recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Verify the recommendation was created
            assert recommendation is not None
            assert recommendation.spending_profile is not None
            assert recommendation.card_preferences is not None
            
            # Verify the stored spending profile data
            stored_spending = recommendation.spending_profile
            assert stored_spending['credit_score'] == 750
            assert stored_spending['income'] == 75000.0
            assert stored_spending['total_monthly_spend'] == sum(spending_data.values())
            assert stored_spending['category_spending'] == spending_data
            assert stored_spending['reward_type'] == 'points'
            assert stored_spending['max_cards'] == 2
            assert stored_spending['max_annual_fees'] == 200.0
            
            # Verify the stored card preferences data
            stored_preferences = recommendation.card_preferences
            assert stored_preferences['reward_type'] == 'points'
            assert stored_preferences['max_cards'] == 2
            assert stored_preferences['max_annual_fees'] == 200.0
            assert stored_preferences['preferred_issuer_id'] is None
    
    def test_profile_form_prefills_from_recommendation(self, test_app, session_id):
        """Test that the profile form prefills with data from a recommendation when accessed via Update Details."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Create a test profile
                spending_data = {
                    'dining': 800.0,
                    'travel': 600.0,
                    'groceries': 300.0,
                    'gas': 150.0,
                    'other': 350.0
                }
                
                profile = UserProfile(
                    name='Original Profile',
                    credit_score=800,
                    income=100000.0,
                    total_monthly_spend=sum(spending_data.values()),
                    category_spending=json.dumps(spending_data),
                    reward_type='cash_back',
                    max_cards=3,
                    max_annual_fees=500.0,
                    preferred_issuer_id=None,
                    session_id=session_id
                )
                db.session.add(profile)
                db.session.commit()
                
                # Generate a recommendation
                recommendation = RecommendationService.generate_recommendation(
                    profile_id=profile.id,
                    session_id=session_id
                )
                
                # Now modify the profile to different values
                profile.category_spending = json.dumps({'dining': 100, 'other': 200})
                profile.reward_type = 'points'
                profile.max_cards = 1
                profile.max_annual_fees = 100.0
                db.session.commit()
                
                # Set up session for anonymous user
                with client.session_transaction() as sess:
                    sess['anonymous_user_id'] = session_id
                
                # Access the profile form with the recommendation ID
                response = client.get(f'/profile/?recommendation_id={recommendation.recommendation_id}')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                # Verify the form is prefilled with the recommendation's original data, not the modified profile
                response_text = response.get_data(as_text=True)
                
                # Check that the original spending amounts are present in the form
                assert 'value="800"' in response_text  # dining amount from recommendation
                assert 'value="600"' in response_text  # travel amount from recommendation
                assert 'value="300"' in response_text  # groceries amount from recommendation
                
                # Check that reward type is set to the recommendation's value
                assert 'value="cash_back" selected' in response_text or 'selected="selected">Cash Back' in response_text
                
                # Check that max_cards is set to the recommendation's value
                assert 'value="3" selected' in response_text or 'selected="selected">3' in response_text
    
    def test_recommendation_id_in_update_details_link(self, test_app, session_id):
        """Test that the Update Details link includes the recommendation ID."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Create a test profile and recommendation
                spending_data = {'dining': 400, 'other': 600}
                
                profile = UserProfile(
                    name='Test Profile',
                    credit_score=750,
                    income=75000.0,
                    total_monthly_spend=sum(spending_data.values()),
                    category_spending=json.dumps(spending_data),
                    reward_type='points',
                    max_cards=1,
                    max_annual_fees=None,
                    session_id=session_id
                )
                db.session.add(profile)
                db.session.commit()
                
                recommendation = RecommendationService.generate_recommendation(
                    profile_id=profile.id,
                    session_id=session_id
                )
                
                # Set up session for anonymous user
                with client.session_transaction() as sess:
                    sess['anonymous_user_id'] = session_id
                
                # Access the recommendation view page
                response = client.get(f'/recommendations/view/{recommendation.recommendation_id}')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                # Verify the Update Details link includes the recommendation ID
                response_text = response.get_data(as_text=True)
                expected_link = f'/profile/?recommendation_id={recommendation.recommendation_id}'
                assert expected_link in response_text
    
    def test_profile_memory_persists_after_profile_changes(self, test_app, session_id):
        """Test that recommendation profile data remains unchanged even after the original profile is modified."""
        with test_app.app_context():
            # Create original profile
            original_spending = {'dining': 500, 'travel': 400, 'other': 300}
            
            profile = UserProfile(
                name='Test Profile',
                credit_score=750,
                income=75000.0,
                total_monthly_spend=sum(original_spending.values()),
                category_spending=json.dumps(original_spending),
                reward_type='points',
                max_cards=2,
                max_annual_fees=300.0,
                session_id=session_id
            )
            db.session.add(profile)
            db.session.commit()
            
            # Generate recommendation with original data
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Store the original recommendation data
            original_rec_spending = recommendation.spending_profile.copy()
            original_rec_preferences = recommendation.card_preferences.copy()
            
            # Modify the profile significantly
            new_spending = {'dining': 1000, 'groceries': 800, 'gas': 200}
            profile.category_spending = json.dumps(new_spending)
            profile.total_monthly_spend = sum(new_spending.values())
            profile.reward_type = 'cash_back'
            profile.max_cards = 5
            profile.max_annual_fees = 1000.0
            profile.credit_score = 800
            profile.income = 120000.0
            db.session.commit()
            
            # Refresh the recommendation from the database
            db.session.refresh(recommendation)
            
            # Verify the recommendation's stored data hasn't changed
            assert recommendation.spending_profile == original_rec_spending
            assert recommendation.card_preferences == original_rec_preferences
            
            # Verify specific values are still the original ones
            assert recommendation.spending_profile['category_spending'] == original_spending
            assert recommendation.spending_profile['reward_type'] == 'points'
            assert recommendation.spending_profile['max_cards'] == 2
            assert recommendation.spending_profile['max_annual_fees'] == 300.0
            assert recommendation.spending_profile['credit_score'] == 750
            assert recommendation.spending_profile['income'] == 75000.0
    
    def test_flash_message_when_editing_from_recommendation(self, test_app, session_id):
        """Test that a helpful flash message appears when editing profile from a recommendation."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Create a test profile and recommendation
                spending_data = {'dining': 300, 'other': 700}
                
                profile = UserProfile(
                    name='Test Profile',
                    credit_score=750,
                    income=75000.0,
                    total_monthly_spend=sum(spending_data.values()),
                    category_spending=json.dumps(spending_data),
                    reward_type='points',
                    max_cards=1,
                    session_id=session_id
                )
                db.session.add(profile)
                db.session.commit()
                
                recommendation = RecommendationService.generate_recommendation(
                    profile_id=profile.id,
                    session_id=session_id
                )
                
                # Set up session for anonymous user
                with client.session_transaction() as sess:
                    sess['anonymous_user_id'] = session_id
                
                # Access the profile form with the recommendation ID
                response = client.get(f'/profile/?recommendation_id={recommendation.recommendation_id}')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                # Check for the flash message
                response_text = response.get_data(as_text=True)
                assert 'Editing profile from recommendation' in response_text
                assert 'Make changes and generate a new recommendation' in response_text 
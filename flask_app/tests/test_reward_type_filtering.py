"""
Test reward type filtering in credit card recommendations.

This module tests that the recommendation engine properly filters credit cards
based on the user's reward type preference (points, cash_back, miles, hotel).
"""

import pytest
import json
import uuid
from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard, CardIssuer
from app.blueprints.recommendations.services import RecommendationService


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
def session_id():
    """Generate a unique session ID for each test."""
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def sample_issuer(test_app):
    """Create a sample card issuer for testing."""
    with test_app.app_context():
        # Clear existing issuers to avoid conflicts
        CardIssuer.query.delete()
        db.session.commit()
        
        issuer = CardIssuer(name='Test Bank')
        db.session.add(issuer)
        db.session.commit()
        return issuer


def _add_card(name: str, issuer_id: int, reward_type: str, annual_fee: float, 
              reward_value_multiplier: float, signup_bonus_points: int, 
              signup_bonus_value: float, rewards: list[dict]):
    """Helper function to add a credit card."""
    card = CreditCard(
        name=name,
        issuer_id=issuer_id,
        reward_type=reward_type,
        annual_fee=annual_fee,
        reward_value_multiplier=reward_value_multiplier,
        signup_bonus_points=signup_bonus_points,
        signup_bonus_value=signup_bonus_value,
        signup_bonus_min_spend=1000,
        signup_bonus_max_months=3,
        reward_categories=json.dumps(rewards),
    )
    db.session.add(card)
    db.session.commit()
    return card


@pytest.fixture(scope="function")
def sample_cards(test_app, sample_issuer):
    """Create sample credit cards with different reward types."""
    with test_app.app_context():
        # Clear existing cards to avoid conflicts
        CreditCard.query.delete()
        db.session.commit()
        
        # Merge issuer back into current session
        issuer = db.session.merge(sample_issuer)
        
        cards = {}
        
        # Points card
        cards['points'] = _add_card(
            name='Premium Points Card',
            issuer_id=issuer.id,
            reward_type='points',
            annual_fee=95,
            reward_value_multiplier=0.0125,
            signup_bonus_points=50000,
            signup_bonus_value=625,  # 50000 * 0.0125
            rewards=[
                {'category': 'dining', 'rate': 3.0},
                {'category': 'travel', 'rate': 2.0},
                {'category': 'other', 'rate': 1.0}
            ]
        )
        
        # Cash back card
        cards['cash_back'] = _add_card(
            name='Cash Back Rewards Card',
            issuer_id=issuer.id,
            reward_type='cash_back',
            annual_fee=0,
            reward_value_multiplier=0.01,
            signup_bonus_points=0,
            signup_bonus_value=200,
            rewards=[
                {'category': 'groceries', 'rate': 2.0},
                {'category': 'gas', 'rate': 2.0},
                {'category': 'other', 'rate': 1.0}
            ]
        )
        
        # Miles card
        cards['miles'] = _add_card(
            name='Travel Miles Card',
            issuer_id=issuer.id,
            reward_type='miles',
            annual_fee=150,
            reward_value_multiplier=0.015,
            signup_bonus_points=40000,
            signup_bonus_value=600,  # 40000 * 0.015
            rewards=[
                {'category': 'travel', 'rate': 3.0},
                {'category': 'dining', 'rate': 2.0},
                {'category': 'other', 'rate': 1.0}
            ]
        )
        
        # Hotel card
        cards['hotel'] = _add_card(
            name='Hotel Rewards Card',
            issuer_id=issuer.id,
            reward_type='hotel',
            annual_fee=75,
            reward_value_multiplier=0.01,
            signup_bonus_points=30000,
            signup_bonus_value=300,  # 30000 * 0.01
            rewards=[
                {'category': 'travel', 'rate': 4.0},
                {'category': 'other', 'rate': 1.0}
            ]
        )
        
        return cards


def _create_profile(spending: dict, reward_type: str, max_cards: int, max_fees, session_id):
    """Helper function to create a user profile."""
    profile = UserProfile(
        session_id=session_id,
        name='Test Profile',
        credit_score=750,
        income=75000,
        total_monthly_spend=sum(spending.values()),
        category_spending=json.dumps(spending),
        reward_type=reward_type,
        max_cards=max_cards,
        max_annual_fees=max_fees if max_fees is not None else None,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


class TestRewardTypeFiltering:
    """Test cases for reward type filtering in recommendations."""
    
    def test_points_filtering(self, test_app, sample_cards, session_id):
        """Test that profiles with points preference only get points cards."""
        with test_app.app_context():
            spending = {'dining': 500, 'travel': 300, 'other': 600}
            profile = _create_profile(spending, 'points', max_cards=3, max_fees=500, session_id=session_id)
            
            # Generate recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Get recommended cards
            recommended_card_ids = recommendation.recommended_sequence
            recommended_cards = [CreditCard.query.get(card_id) for card_id in recommended_card_ids]
            
            # Verify all cards are points cards
            assert len(recommended_cards) > 0, "Should recommend at least one card"
            for card in recommended_cards:
                assert card.reward_type == 'points', f"Card {card.name} should be points type, got {card.reward_type}"
    
    def test_cash_back_filtering(self, test_app, sample_cards, session_id):
        """Test that profiles with cash_back preference only get cash_back cards."""
        with test_app.app_context():
            spending = {'groceries': 400, 'gas': 200, 'other': 600}
            profile = _create_profile(spending, 'cash_back', max_cards=3, max_fees=500, session_id=session_id)
            
            # Generate recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Get recommended cards
            recommended_card_ids = recommendation.recommended_sequence
            recommended_cards = [CreditCard.query.get(card_id) for card_id in recommended_card_ids]
            
            # Verify all cards are cash back cards
            assert len(recommended_cards) > 0, "Should recommend at least one card"
            for card in recommended_cards:
                assert card.reward_type == 'cash_back', f"Card {card.name} should be cash_back type, got {card.reward_type}"
    
    def test_miles_filtering(self, test_app, sample_cards, session_id):
        """Test that profiles with miles preference only get miles cards."""
        with test_app.app_context():
            spending = {'travel': 500, 'dining': 300, 'other': 400}
            profile = _create_profile(spending, 'miles', max_cards=3, max_fees=500, session_id=session_id)
            
            # Generate recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Get recommended cards
            recommended_card_ids = recommendation.recommended_sequence
            recommended_cards = [CreditCard.query.get(card_id) for card_id in recommended_card_ids]
            
            # Verify all cards are miles cards
            assert len(recommended_cards) > 0, "Should recommend at least one card"
            for card in recommended_cards:
                assert card.reward_type == 'miles', f"Card {card.name} should be miles type, got {card.reward_type}"
    
    def test_hotel_filtering(self, test_app, sample_cards, session_id):
        """Test that profiles with hotel preference only get hotel cards."""
        with test_app.app_context():
            spending = {'travel': 400, 'other': 600}
            profile = _create_profile(spending, 'hotel', max_cards=3, max_fees=500, session_id=session_id)
            
            # Generate recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Get recommended cards
            recommended_card_ids = recommendation.recommended_sequence
            recommended_cards = [CreditCard.query.get(card_id) for card_id in recommended_card_ids]
            
            # Verify all cards are hotel cards
            assert len(recommended_cards) > 0, "Should recommend at least one card"
            for card in recommended_cards:
                assert card.reward_type == 'hotel', f"Card {card.name} should be hotel type, got {card.reward_type}"
    
    def test_reward_type_change(self, test_app, sample_cards, session_id):
        """Test that changing reward type preference changes recommendations."""
        with test_app.app_context():
            spending = {'dining': 500, 'groceries': 400, 'travel': 300, 'other': 300}
            
            # Start with points preference
            profile = _create_profile(spending, 'points', max_cards=3, max_fees=500, session_id=session_id)
            
            recommendation1 = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            cards1 = [CreditCard.query.get(card_id) for card_id in recommendation1.recommended_sequence]
            
            # Change to cash back preference
            profile.reward_type = 'cash_back'
            db.session.commit()
            
            recommendation2 = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            cards2 = [CreditCard.query.get(card_id) for card_id in recommendation2.recommended_sequence]
            
            # Verify the recommendations are different
            card1_types = {card.reward_type for card in cards1}
            card2_types = {card.reward_type for card in cards2}
            
            assert 'points' in card1_types, "First recommendation should include points cards"
            assert 'cash_back' in card2_types, "Second recommendation should include cash_back cards"
            assert card1_types != card2_types, "Recommendations should be different for different reward types"
    
    def test_no_cards_of_preferred_type(self, test_app, sample_issuer, session_id):
        """Test behavior when no cards match the preferred reward type."""
        with test_app.app_context():
            # Clear existing cards
            CreditCard.query.delete()
            db.session.commit()
            
            # Merge issuer back into current session
            issuer = db.session.merge(sample_issuer)
            
            # Create only points cards
            _add_card(
                name='Only Points Card',
                issuer_id=issuer.id,
                reward_type='points',
                annual_fee=0,
                reward_value_multiplier=0.01,
                signup_bonus_points=10000,
                signup_bonus_value=100,
                rewards=[{'category': 'other', 'rate': 1.0}]
            )
            
            spending = {'other': 1000}
            # Set profile to prefer miles (which don't exist)
            profile = _create_profile(spending, 'miles', max_cards=3, max_fees=500, session_id=session_id)
            
            # Generate recommendation
            recommendation = RecommendationService.generate_recommendation(
                profile_id=profile.id,
                session_id=session_id
            )
            
            # Should get no recommendations since no miles cards exist
            assert len(recommendation.recommended_sequence) == 0, "Should get no recommendations when no matching cards exist"
    
    def test_estimated_value_calculation(self, test_app, sample_cards, session_id):
        """Test that estimated value is calculated correctly using reward_value_multiplier."""
        with test_app.app_context():
            # Get a specific card to test
            points_card = sample_cards['points']
            points_card = db.session.merge(points_card)  # Merge into current session
            
            # Verify estimated value calculation
            expected_value = points_card.signup_bonus_points * points_card.reward_value_multiplier
            assert points_card.estimated_value == expected_value, f"Estimated value should be {expected_value}, got {points_card.estimated_value}"
            
            # Test with different multiplier
            points_card.reward_value_multiplier = 0.02
            points_card.signup_bonus_points = 25000
            db.session.commit()
            
            expected_value = 25000 * 0.02  # 500
            assert points_card.estimated_value == expected_value, f"Updated estimated value should be {expected_value}, got {points_card.estimated_value}"


if __name__ == '__main__':
    pytest.main([__file__]) 
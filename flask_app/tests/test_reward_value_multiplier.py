import pytest
from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.blueprints.recommendations.services import RecommendationService
import json


@pytest.fixture(scope='function')
def app():
    """Create application for the tests."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def test_issuer(app):
    """Create a test card issuer."""
    with app.app_context():
        issuer = CardIssuer(name='Test Multiplier Bank')
        db.session.add(issuer)
        db.session.commit()
        return issuer


def test_reward_value_multiplier_calculation(app, test_issuer):
    """Test that reward_value_multiplier is correctly applied to convert points to dollars."""
    with app.app_context():
        # Create a card with 1.5 cents per point multiplier
        card = CreditCard(
            name='Test Points Card',
            issuer_id=test_issuer.id,
            annual_fee=0,
            reward_type='points',
            reward_value_multiplier=1.5,  # 1.5 cents per point
            reward_categories='[{"category": "dining", "rate": 3.0}, {"category": "other", "rate": 1.0}]',
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Test spending: $100/month on dining
        monthly_spending = {'dining': 100}
        
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculation (NEW SYSTEM):
        # Annual spending: $100 * 12 = $1,200
        # Points earned: $1,200 * 3% = 36 points
        # Dollar value: 36 points * 1.5 = $54 (1.5 dollar value per point)
        expected_points = 1200 * 0.03  # 36 points
        expected_value = expected_points * 1.5  # $54 (1.5 dollar value per point)
        
        dining_rewards = result['rewards_by_category']['dining']
        
        assert dining_rewards['points_earned'] == expected_points
        assert abs(dining_rewards['value'] - expected_value) < 0.01
        assert abs(result['annual_value'] - expected_value) < 0.01


def test_reward_value_multiplier_with_limits(app, test_issuer):
    """Test that reward_value_multiplier works correctly with spending limits."""
    with app.app_context():
        # Create a card with spending limit and multiplier
        card = CreditCard(
            name='Test Limited Card',
            issuer_id=test_issuer.id,
            annual_fee=0,
            reward_type='points',
            reward_value_multiplier=1.0,  # 1 cent per point
            reward_categories='[{"category": "gas", "rate": 5.0, "limit": 1000}, {"category": "other", "rate": 1.0}]',
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Test spending: $200/month on gas = $2,400/year
        # First $1,000 at 5%, remaining $1,400 at 1%
        monthly_spending = {'gas': 200}
        
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculation (NEW SYSTEM):
        # Main spend: $1,000 * 5% = 50 points
        # Base spend: $1,400 * 1% = 14 points
        # Total points: 64 points
        # Dollar value: 64 points * 1.0 = $64 (1.0 dollar value per point)
        expected_main_points = 1000 * 0.05  # 50 points
        expected_base_points = 1400 * 0.01  # 14 points
        expected_total_points = expected_main_points + expected_base_points  # 64 points
        expected_value = expected_total_points * 1.0  # $64 (1.0 dollar value per point)
        
        gas_rewards = result['rewards_by_category']['gas']
        
        assert abs(gas_rewards['points_earned'] - expected_total_points) < 0.01
        assert abs(gas_rewards['value'] - expected_value) < 0.01
        assert abs(result['annual_value'] - expected_value) < 0.01


def test_reward_value_multiplier_high_value_example(app, test_issuer):
    """Test the user's example: $100/month * 3% * multiplier = $4.50/month."""
    with app.app_context():
        # To get $4.50/month ($54/year) from $100/month at 3%:
        # $1,200/year * 3% = 36 points
        # 36 points * multiplier = $54
        # multiplier = $54 / 36 = $1.50 per point
        card = CreditCard(
            name='High Value Card',
            issuer_id=test_issuer.id,
            annual_fee=0,
            reward_type='travel',
            reward_value_multiplier=1.5,  # $1.50 per point (high-value travel card)
            reward_categories='[{"category": "dining", "rate": 3.0}, {"category": "other", "rate": 1.0}]',
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Test spending: $100/month on dining
        monthly_spending = {'dining': 100}
        
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected (NEW SYSTEM): $100 * 12 * 3% * 1.5 = $54/year = $4.50/month
        expected_annual_value = 100 * 12 * 0.03 * 1.5  # $54 (1.5 dollar value per point)
        expected_monthly_value = expected_annual_value / 12  # $4.50
        
        dining_rewards = result['rewards_by_category']['dining']
        
        assert abs(dining_rewards['value'] - expected_annual_value) < 0.01
        assert abs(result['annual_value'] - expected_annual_value) < 0.01
        
        # Verify monthly value
        monthly_value = result['annual_value'] / 12
        assert abs(monthly_value - expected_monthly_value) < 0.01 
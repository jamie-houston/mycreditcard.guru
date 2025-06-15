import pytest
import json
from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.blueprints.recommendations.services import RecommendationService


class TestCalculationBugFix:
    """Test to demonstrate and fix the calculation bug"""
    
    @pytest.fixture(scope='function')
    def app(self):
        """Create application for the tests."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def test_issuer(self, app):
        """Create a test card issuer."""
        with app.app_context():
            issuer = CardIssuer(name='Test Bank')
            db.session.add(issuer)
            db.session.commit()
            return issuer
    
    def test_user_example_demonstrates_bug(self, app, test_issuer):
        """
        Test the user's exact example to demonstrate the calculation bug.
        
        User expects:
        - Credit card with 2% other rate, reward value multiplier of 0.015
        - Profile with spending of $100 in travel category  
        - Result: card with annual value of $36 (100*12*0.015*2)
        
        But current code gives: $0.36 (100*12*(2/100)*0.015)
        """
        with app.app_context():
            # Create card exactly as user described
            card = CreditCard(
                name='User Example Card',
                issuer_id=test_issuer.id,
                annual_fee=0,
                reward_type='cash_back',
                reward_value_multiplier=0.015,
                reward_categories=json.dumps([{"category": "other", "rate": 2.0}]),
                is_active=True
            )
            db.session.add(card)
            db.session.commit()
            
            # Test with user's spending profile
            monthly_spending = {"travel": 100}
            result = RecommendationService.calculate_card_value(card, monthly_spending)
            
            print(f"\n=== User's Example Test ===")
            print(f"Monthly spending: {monthly_spending}")
            print(f"Card reward categories: {card.reward_categories}")
            print(f"Card reward value multiplier: {card.reward_value_multiplier}")
            print(f"Actual result: {result}")
            
            # What user expects
            user_expected = 100 * 12 * 0.015 * 2  # $36
            print(f"User expects: ${user_expected}")
            
            # What current code gives
            current_result = result['annual_value']
            print(f"Current code gives: ${current_result}")
            
            # Demonstrate the bug
            assert abs(current_result - 0.36) < 0.01, f"Current code should give $0.36, got ${current_result}"
            assert abs(user_expected - 36.0) < 0.01, f"User expects $36, calculated ${user_expected}"
            
            # Show the difference
            difference_factor = user_expected / current_result
            print(f"Difference factor: {difference_factor}x")
            assert abs(difference_factor - 100.0) < 0.01, "The bug is exactly a factor of 100"
    
    def test_calculation_breakdown(self, app, test_issuer):
        """Break down the calculation to show exactly where the issue is"""
        with app.app_context():
            card = CreditCard(
                name='Debug Card',
                issuer_id=test_issuer.id,
                annual_fee=0,
                reward_type='cash_back',
                reward_value_multiplier=0.015,
                reward_categories=json.dumps([{"category": "other", "rate": 2.0}]),
                is_active=True
            )
            db.session.add(card)
            db.session.commit()
            
            monthly_spending = {"travel": 100}
            result = RecommendationService.calculate_card_value(card, monthly_spending)
            
            print(f"\n=== Calculation Breakdown ===")
            
            # Extract the calculation details
            travel_details = result['rewards_by_category']['travel']
            print(f"Travel category details: {travel_details}")
            
            # Manual step-by-step calculation
            monthly_spend = 100
            annual_spend = monthly_spend * 12  # 1200
            reward_rate = 2.0  # 2%
            multiplier = 0.015
            
            # Current code logic
            points_earned = annual_spend * (reward_rate / 100)  # 1200 * 0.02 = 24
            dollar_value = points_earned * multiplier  # 24 * 0.015 = 0.36
            
            print(f"Step-by-step current logic:")
            print(f"  Annual spend: ${annual_spend}")
            print(f"  Reward rate: {reward_rate}% -> {reward_rate/100} (decimal)")
            print(f"  Points earned: {annual_spend} * {reward_rate/100} = {points_earned}")
            print(f"  Dollar value: {points_earned} * {multiplier} = ${dollar_value}")
            
            # Verify our understanding matches the actual result
            assert abs(travel_details['points_earned'] - points_earned) < 0.01
            assert abs(travel_details['value'] - dollar_value) < 0.01
            assert abs(result['annual_value'] - dollar_value) < 0.01
            
            # User's expected logic (what they think should happen)
            user_expected = monthly_spend * 12 * reward_rate * multiplier  # 100 * 12 * 2 * 0.015 = 36
            print(f"\nUser's expected logic:")
            print(f"  {monthly_spend} * 12 * {reward_rate} * {multiplier} = ${user_expected}")
            
            print(f"\nThe issue: reward_rate is divided by 100 in the code, but user expects it to be used directly")
    
    def test_proposed_fix_approach_1_adjust_multiplier(self, app, test_issuer):
        """
        Test approach 1: Keep current logic but adjust multiplier values.
        
        To get user's expected $36 with current logic:
        - Current: annual_spend * (rate/100) * multiplier = 1200 * 0.02 * multiplier = 36
        - So: multiplier = 36 / (1200 * 0.02) = 36 / 24 = 1.5
        """
        with app.app_context():
            card = CreditCard(
                name='Fixed Card - Approach 1',
                issuer_id=test_issuer.id,
                annual_fee=0,
                reward_type='cash_back',
                reward_value_multiplier=1.5,  # Adjusted from 0.015 to 1.5
                reward_categories=json.dumps([{"category": "other", "rate": 2.0}]),
                is_active=True
            )
            db.session.add(card)
            db.session.commit()
            
            monthly_spending = {"travel": 100}
            result = RecommendationService.calculate_card_value(card, monthly_spending)
            
            print(f"\n=== Fix Approach 1: Adjust Multiplier ===")
            print(f"Adjusted multiplier to: {card.reward_value_multiplier}")
            print(f"Result: {result}")
            
            # Should now give user's expected $36
            expected_value = 36.0
            actual_value = result['annual_value']
            
            print(f"Expected: ${expected_value}")
            print(f"Actual: ${actual_value}")
            
            assert abs(actual_value - expected_value) < 0.01, f"Fix approach 1 failed: expected ${expected_value}, got ${actual_value}"
    
    def test_proposed_fix_approach_2_change_calculation(self, app, test_issuer):
        """
        Test approach 2: Change the calculation logic to not divide by 100.
        
        This would require modifying the RecommendationService.calculate_card_value method.
        For now, we'll just demonstrate what the calculation should be.
        """
        print(f"\n=== Fix Approach 2: Change Calculation Logic ===")
        
        # Simulate the fixed calculation
        monthly_spend = 100
        annual_spend = monthly_spend * 12  # 1200
        reward_rate = 2.0  # Store as 2.0 but treat as 0.02 directly
        multiplier = 0.015
        
        # Current (buggy) logic
        current_points = annual_spend * (reward_rate / 100)  # 1200 * 0.02 = 24
        current_value = current_points * multiplier  # 24 * 0.015 = 0.36
        
        # Proposed fixed logic - don't divide by 100
        fixed_points = annual_spend * (reward_rate / 100)  # Keep this part the same for now
        # But adjust how we interpret the multiplier or rate
        
        # Actually, the cleanest fix might be to store rates as decimals (0.02 instead of 2.0)
        # Or adjust the multiplier values to account for the /100
        
        print(f"Current logic gives: ${current_value}")
        print(f"User expects: ${100 * 12 * 2 * 0.015}")
        print(f"The issue is in how we interpret the reward_rate and multiplier relationship")
        
        # For this test, we'll just verify our understanding
        assert abs(current_value - 0.36) < 0.01
        assert abs(100 * 12 * 2 * 0.015 - 36.0) < 0.01 
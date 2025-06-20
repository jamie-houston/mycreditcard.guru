import unittest
import json
from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category
from app.blueprints.recommendations.services import RecommendationService


class TestCalculationBugFix(unittest.TestCase):
    """Test to demonstrate and verify the new calculation system"""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test categories
        categories = [
            Category(name='travel', display_name='Travel'),
            Category(name='other', display_name='Other'),
            Category(name='dining', display_name='Dining'),
        ]
        for category in categories:
            db.session.add(category)
        
        # Create test issuer
        self.test_issuer = CardIssuer(name='Calculation Test Bank')
        db.session.add(self.test_issuer)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_example_new_system(self):
        """
        Test the user's example with the new calculation system.
        
        New system:
        - Credit card with 2% other rate, reward value multiplier of 1.5
        - Profile with spending of $100 in travel category  
        - Result: card with annual value of $36 (100*12*0.02*1.5)
        """
        # Create card with new system values
        card = CreditCard(
            name='User Example Card - New System',
            issuer_id=self.test_issuer.id,
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.5,  # New system: 1.5 instead of 0.015
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Add reward category using new system - travel should get 2%
        card.add_reward_category('travel', 2.0)
        card.add_reward_category('other', 1.0)  # Default rate
        db.session.commit()
        
        # Test with user's spending profile
        monthly_spending = {"travel": 100}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        print(f"\n=== User's Example Test - New System ===")
        print(f"Monthly spending: {monthly_spending}")
        print(f"Card reward categories: {card.get_all_rewards()}")
        print(f"Card reward value multiplier: {card.reward_value_multiplier}")
        print(f"Actual result: {result}")
        
        # What user expects with new system
        user_expected = 100 * 12 * 0.02 * 1.5  # $36
        print(f"User expects: ${user_expected}")
        
        # What new system gives
        current_result = result['annual_value']
        print(f"New system gives: ${current_result}")
        
        # Verify the new system works correctly
        self.assertAlmostEqual(current_result, 36.0, places=2, 
                              msg=f"New system should give $36, got ${current_result}")
        self.assertAlmostEqual(user_expected, 36.0, places=2, 
                              msg=f"User expects $36, calculated ${user_expected}")
    
    def test_calculation_breakdown_new_system(self):
        """Break down the calculation to show the new system works correctly"""
        card = CreditCard(
            name='Debug Card - New System',
            issuer_id=self.test_issuer.id,
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.5,  # New system
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Add reward category using new system - travel should get 2%
        card.add_reward_category('travel', 2.0)
        card.add_reward_category('other', 1.0)  # Default rate
        db.session.commit()
        
        monthly_spending = {"travel": 100}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        print(f"\n=== Calculation Breakdown - New System ===")
        
        # Extract the calculation details
        travel_details = result['rewards_by_category']['travel']
        print(f"Travel category details: {travel_details}")
        
        # Manual step-by-step calculation
        monthly_spend = 100
        annual_spend = monthly_spend * 12  # 1200
        reward_rate = 2.0  # 2%
        multiplier = 1.5  # New system
        
        # New system logic
        points_earned = annual_spend * (reward_rate / 100)  # 1200 * 0.02 = 24
        dollar_value = points_earned * multiplier  # 24 * 1.5 = 36
        
        print(f"Step-by-step new system logic:")
        print(f"  Annual spend: ${annual_spend}")
        print(f"  Reward rate: {reward_rate}% -> {reward_rate/100} (decimal)")
        print(f"  Points earned: {annual_spend} * {reward_rate/100} = {points_earned}")
        print(f"  Dollar value: {points_earned} * {multiplier} = ${dollar_value}")
        
        # Verify our understanding matches the actual result
        self.assertAlmostEqual(travel_details['points_earned'], points_earned, places=2)
        self.assertAlmostEqual(travel_details['value'], dollar_value, places=2)
        self.assertAlmostEqual(result['annual_value'], dollar_value, places=2)
    
    def test_new_system_with_different_multipliers(self):
        """
        Test the new system with different multiplier values to ensure it works correctly.
        """
        # Test with 1.0 multiplier (cash back)
        cash_card = CreditCard(
            name='Cash Back Card',
            issuer_id=self.test_issuer.id,
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.0,  # 1.0 for cash back
            is_active=True
        )
        db.session.add(cash_card)
        
        # Test with 1.6 multiplier (premium points)
        points_card = CreditCard(
            name='Premium Points Card',
            issuer_id=self.test_issuer.id,
            annual_fee=95,
            reward_type='points',
            reward_value_multiplier=1.6,  # 1.6 for premium points
            is_active=True
        )
        db.session.add(points_card)
        db.session.commit()
        
        # Add reward categories using new system - travel should get 2%
        cash_card.add_reward_category('travel', 2.0)
        cash_card.add_reward_category('other', 1.0)
        points_card.add_reward_category('travel', 2.0)
        points_card.add_reward_category('other', 1.0)
        db.session.commit()
        
        monthly_spending = {"travel": 100}
        
        # Test cash back card
        cash_result = RecommendationService.calculate_card_value(cash_card, monthly_spending)
        expected_cash = 100 * 12 * 0.02 * 1.0  # $24
        self.assertAlmostEqual(cash_result['annual_value'], 24.0, places=2, 
                              msg=f"Cash card should give $24, got ${cash_result['annual_value']}")
        
        # Test points card
        points_result = RecommendationService.calculate_card_value(points_card, monthly_spending)
        expected_points = 100 * 12 * 0.02 * 1.6  # $38.4
        self.assertAlmostEqual(points_result['annual_value'], 38.4, places=2, 
                              msg=f"Points card should give $38.4, got ${points_result['annual_value']}")
        
        print(f"\n=== Multiple Multiplier Test ===")
        print(f"Cash back card (1.0x): ${cash_result['annual_value']}")
        print(f"Points card (1.6x): ${points_result['annual_value']}")
    
    def test_backward_compatibility_property(self):
        """
        Test that the point_value property still works for backward compatibility.
        """
        card = CreditCard(
            name='Backward Compatibility Card',
            issuer_id=self.test_issuer.id,
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.5,
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Add reward category using new system
        card.add_reward_category('other', 1.0)  # Just a default rate for this test
        db.session.commit()
        
        # Test that point_value property returns the same as reward_value_multiplier
        self.assertEqual(card.point_value, card.reward_value_multiplier)
        
        # Test that setting point_value updates reward_value_multiplier
        card.point_value = 2.0
        self.assertEqual(card.reward_value_multiplier, 2.0)
        
        print(f"\n=== Backward Compatibility Test ===")
        print(f"point_value property works correctly")


if __name__ == '__main__':
    unittest.main() 
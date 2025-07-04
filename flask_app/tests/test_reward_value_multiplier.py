import unittest
from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category
from app.blueprints.recommendations.services import RecommendationService
import json


class TestRewardValueMultiplier(unittest.TestCase):
    """Test reward value multiplier calculations"""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test categories
        categories = [
            Category(name='dining', display_name='Dining'),
            Category(name='other', display_name='Other'),
            Category(name='travel', display_name='Travel'),
            Category(name='gas', display_name='Gas'),
        ]
        for category in categories:
            db.session.add(category)
        
        # Create test issuer
        self.test_issuer = CardIssuer(name='Test Multiplier Bank')
        db.session.add(self.test_issuer)
        db.session.commit()
    
    def create_card_with_rewards(self, name, annual_fee=0, reward_type='cash_back', 
                                reward_value_multiplier=1.0, reward_categories=None):
        """Helper to create a card with the new reward system"""
        card = CreditCard(
            name=name,
            issuer_id=self.test_issuer.id,
            annual_fee=annual_fee,
            reward_type=reward_type,
            reward_value_multiplier=reward_value_multiplier,
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Add reward categories
        if reward_categories:
            for reward in reward_categories:
                card.add_reward_category(
                    reward['category'], 
                    reward['rate'],
                    limit=reward.get('limit')
                )
        
        db.session.commit()
        return card
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_reward_value_multiplier_calculation(self):
        """Test that reward_value_multiplier is correctly applied to convert points to dollars."""
        # Create a card with 1.5 cents per point multiplier
        card = self.create_card_with_rewards(
            name='Test Points Card',
            reward_type='points',
            reward_value_multiplier=1.5,  # 1.5 cents per point
            reward_categories=[
                {"category": "dining", "rate": 3.0}, 
                {"category": "other", "rate": 1.0}
            ]
        )
        
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
        
        self.assertEqual(dining_rewards['points_earned'], expected_points)
        self.assertAlmostEqual(dining_rewards['value'], expected_value, places=2)
        self.assertAlmostEqual(result['annual_value'], expected_value, places=2)

    def test_reward_value_multiplier_with_limits(self):
        """Test that reward_value_multiplier works correctly with spending limits."""
        # Create a card with spending limit and multiplier
        card = self.create_card_with_rewards(
            name='Test Limited Card',
            reward_type='points',
            reward_value_multiplier=1.0,  # 1 cent per point
            reward_categories=[
                {"category": "gas", "rate": 5.0, "limit": 1000}, 
                {"category": "other", "rate": 1.0}
            ]
        )
        
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
        
        self.assertAlmostEqual(gas_rewards['points_earned'], expected_total_points, places=2)
        self.assertAlmostEqual(gas_rewards['value'], expected_value, places=2)
        self.assertAlmostEqual(result['annual_value'], expected_value, places=2)

    def test_reward_value_multiplier_high_value_example(self):
        """Test the user's example: $100/month * 3% * multiplier = $4.50/month."""
        # To get $4.50/month ($54/year) from $100/month at 3%:
        # $1,200/year * 3% = 36 points
        # 36 points * multiplier = $54
        # multiplier = $54 / 36 = $1.50 per point
        card = self.create_card_with_rewards(
            name='High Value Card',
            reward_type='travel',
            reward_value_multiplier=1.5,  # $1.50 per point (high-value travel card)
            reward_categories=[
                {"category": "dining", "rate": 3.0}, 
                {"category": "other", "rate": 1.0}
            ]
        )
        
        # Test spending: $100/month on dining
        monthly_spending = {'dining': 100}
        
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected (NEW SYSTEM): $100 * 12 * 3% * 1.5 = $54/year = $4.50/month
        expected_annual_value = 100 * 12 * 0.03 * 1.5  # $54 (1.5 dollar value per point)
        expected_monthly_value = expected_annual_value / 12  # $4.50
        
        dining_rewards = result['rewards_by_category']['dining']
        
        self.assertAlmostEqual(dining_rewards['value'], expected_annual_value, places=2)
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        
        # Verify monthly value
        monthly_value = result['annual_value'] / 12
        self.assertAlmostEqual(monthly_value, expected_monthly_value, places=2)


if __name__ == '__main__':
    unittest.main() 
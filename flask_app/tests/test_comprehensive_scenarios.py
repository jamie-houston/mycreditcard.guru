import unittest
import json
from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category
from app.models.user_data import UserProfile
from app.blueprints.recommendations.services import RecommendationService


class TestComprehensiveScenarios(unittest.TestCase):
    """Comprehensive test scenarios for credit card recommendations"""
    
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
            Category(name='gas', display_name='Gas'),
        ]
        for category in categories:
            db.session.add(category)
        
        # Create test issuer
        self.test_issuer = CardIssuer(name='Comprehensive Test Bank')
        db.session.add(self.test_issuer)
        db.session.commit()
    
    def create_card_with_rewards(self, name, annual_fee=0, reward_type='cash_back', 
                                reward_value_multiplier=1.0, reward_categories=None, 
                                signup_bonus=None):
        """Helper to create a card with the new reward system"""
        card = CreditCard(
            name=name,
            issuer_id=self.test_issuer.id,
            annual_fee=annual_fee,
            reward_type=reward_type,
            reward_value_multiplier=reward_value_multiplier,
            is_active=True
        )
        
        # Handle signup bonus
        if signup_bonus:
            card.update_signup_bonus(
                amount=signup_bonus.get('amount', 0),
                min_spend=signup_bonus.get('min_spend', 0),
                max_months=signup_bonus.get('max_months', 3)
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

    def test_basic_travel_spending_with_other_rate(self):
        """Test travel spending that falls back to 'other' category rate"""
        # Card only has 'other' category, travel spending should use that rate
        card = self.create_card_with_rewards(
            name='Basic 2% Card',
            reward_value_multiplier=1.5,
            reward_categories=[{"category": "other", "rate": 2.0}]
        )
        
        monthly_spending = {"travel": 100}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected: 100*12*0.02*1.5 = 36
        expected_annual_value = 36.0
        expected_net_value = 36.0  # No annual fee
        
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        self.assertAlmostEqual(result['net_value'], expected_net_value, places=2)
        
        # Travel spending should be stored under 'travel' key but use 'other' rate
        self.assertIn('travel', result['rewards_by_category'])
        self.assertAlmostEqual(result['rewards_by_category']['travel']['value'], expected_annual_value, places=2)

    def test_multiple_categories_with_different_rates(self):
        """Test card with multiple reward categories and spending"""
        card = self.create_card_with_rewards(
            name='Multi-Category Card',
            annual_fee=95,
            reward_type='points',
            reward_value_multiplier=1.5,
            reward_categories=[
                {"category": "travel", "rate": 3.0},
                {"category": "dining", "rate": 2.0},
                {"category": "other", "rate": 1.0}
            ]
        )
        
        monthly_spending = {"travel": 100, "dining": 50, "groceries": 200}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculations:
        # Travel: 100*12*0.03*1.5 = 54
        # Dining: 50*12*0.02*1.5 = 18  
        # Groceries: 200*12*0.01*1.5 = 36 (uses 'other' rate)
        # Total: 54 + 18 + 36 = 108
        # Net: 108 - 95 = 13
        
        expected_annual_value = 108.0
        expected_net_value = 13.0
        
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        self.assertAlmostEqual(result['net_value'], expected_net_value, places=2)
        
        # Check individual category values
        self.assertAlmostEqual(result['rewards_by_category']['travel']['value'], 54.0, places=2)
        self.assertAlmostEqual(result['rewards_by_category']['dining']['value'], 18.0, places=2)
        self.assertAlmostEqual(result['rewards_by_category']['groceries']['value'], 36.0, places=2)

    def test_spending_limit_with_overflow(self):
        """Test spending limit where spending exceeds the limit"""
        card = self.create_card_with_rewards(
            name='Gas Rewards Card',
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.0,
            reward_categories=[
                {"category": "gas", "rate": 5.0, "limit": 1000},
                {"category": "other", "rate": 1.0}
            ]
        )
        
        # $200/month = $2400/year, exceeds $1000 limit
        monthly_spending = {"gas": 200}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculation:
        # First $1000 at 5%: 1000*0.05 = 50 points
        # Remaining $1400 at 1%: 1400*0.01 = 14 points  
        # Total: 64 points * 1.0 = $64
        expected_annual_value = 64.0
        
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        
        # Check the breakdown
        gas_details = result['rewards_by_category']['gas']
        self.assertEqual(gas_details['main_spend'], 1000)
        self.assertEqual(gas_details['base_spend'], 1400)
        self.assertEqual(gas_details['main_rate'], 5.0)
        self.assertEqual(gas_details['base_rate'], 1.0)

    def test_signup_bonus_calculation(self):
        """Test card with signup bonus"""
        card = self.create_card_with_rewards(
            name='Signup Bonus Card',
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.0,
            reward_categories=[{"category": "other", "rate": 1.0}],
            signup_bonus={"amount": 200, "min_spend": 1000, "max_months": 3}
        )
        
        # $400/month = $1200 in 3 months, meets signup requirement
        monthly_spending = {"dining": 400}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculation:
        # Regular rewards: 400*12*0.01*1.0 = 48
        # Signup bonus: 200
        # Total: 248
        expected_annual_value = 248.0
        
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        
        # Check that signup bonus is included
        self.assertIn('signup_bonus', result['rewards_by_category'])
        self.assertEqual(result['rewards_by_category']['signup_bonus'], 200)

    def test_high_annual_fee_negative_net_value(self):
        """Test card where annual fee exceeds rewards (negative net value)"""
        card = self.create_card_with_rewards(
            name='Premium Card',
            annual_fee=500,  # High fee
            reward_type='points',
            reward_value_multiplier=1.5,
            reward_categories=[{"category": "other", "rate": 2.0}]
        )
        
        # Low spending: $50/month
        monthly_spending = {"dining": 50}
        result = RecommendationService.calculate_card_value(card, monthly_spending)
        
        # Expected calculation:
        # Annual rewards: 50*12*0.02*1.5 = 18
        # Net value: 18 - 500 = -482
        expected_annual_value = 18.0
        expected_net_value = -482.0
        
        self.assertAlmostEqual(result['annual_value'], expected_annual_value, places=2)
        self.assertAlmostEqual(result['net_value'], expected_net_value, places=2)
        
        # Net value should be negative
        self.assertLess(result['net_value'], 0)

    def test_cash_back_vs_points_multiplier(self):
        """Test different reward types with different multipliers"""
        # Cash back card (1:1 ratio)
        cash_card = self.create_card_with_rewards(
            name='Cash Back Card',
            annual_fee=0,
            reward_type='cash_back',
            reward_value_multiplier=1.0,  # 1:1 for cash back
            reward_categories=[{"category": "dining", "rate": 2.0}]
        )
        
        # Points card (higher value per point)
        points_card = self.create_card_with_rewards(
            name='Points Card',
            annual_fee=0,
            reward_type='points',
            reward_value_multiplier=1.5,  # 1.5 cents per point
            reward_categories=[{"category": "dining", "rate": 2.0}]
        )
        
        monthly_spending = {"dining": 100}
        
        # Test cash back card
        cash_result = RecommendationService.calculate_card_value(cash_card, monthly_spending)
        expected_cash = 100 * 12 * 0.02 * 1.0  # $24
        
        # Test points card  
        points_result = RecommendationService.calculate_card_value(points_card, monthly_spending)
        expected_points = 100 * 12 * 0.02 * 1.5  # $36
        
        self.assertAlmostEqual(cash_result['annual_value'], expected_cash, places=2)
        self.assertAlmostEqual(points_result['annual_value'], expected_points, places=2)
        
        # Points card should have higher value due to multiplier
        self.assertGreater(points_result['annual_value'], cash_result['annual_value'])


if __name__ == '__main__':
    unittest.main() 
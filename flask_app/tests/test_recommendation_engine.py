"""Tests for the recommendation engine."""

import unittest
import json
from app import create_app, db
from app.engine.recommendation import RecommendationEngine
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
from app.models import CardIssuer
from app.blueprints.recommendations.services import RecommendationService


class TestRecommendationEngine(unittest.TestCase):
    """Test cases for the RecommendationEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Only create tables for tests that need database access
        if hasattr(self, '_testMethodName') and 'duplicate_recommendation' in self._testMethodName:
            db.create_all()

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, '_testMethodName') and 'duplicate_recommendation' in self._testMethodName:
            db.session.rollback()
            db.drop_all()
        self.app_context.pop()

    def test_duplicate_recommendation_id_prevention(self):
        """Test that generating the same recommendation twice doesn't cause a UNIQUE constraint error.
        
        This test verifies that when a user generates recommendations multiple times
        with the same profile data, the system returns the existing recommendation
        instead of trying to create a duplicate, which would cause a UNIQUE constraint
        violation on the recommendation_id field.
        """
        # Create test issuer
        issuer = CardIssuer(name='Test Bank')
        db.session.add(issuer)
        db.session.commit()
        
        # Create test cards
        card1 = CreditCard(
            name='Test Card 1',
            issuer_id=issuer.id,
            annual_fee=95.0,
            point_value=0.01,
            reward_categories=json.dumps([
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 2.0},
                {"category": "other", "rate": 1.0}
            ]),
            signup_bonus_value=500.0
        )
        card2 = CreditCard(
            name='Test Card 2',
            issuer_id=issuer.id,
            annual_fee=0.0,
            point_value=0.01,
            reward_categories=json.dumps([
                {"category": "groceries", "rate": 2.0},
                {"category": "gas", "rate": 2.0},
                {"category": "other", "rate": 1.0}
            ]),
            signup_bonus_value=200.0
        )
        db.session.add(card1)
        db.session.add(card2)
        db.session.commit()
        
        # Create test profile
        profile = UserProfile(
            name='Test Profile',
            credit_score=750,
            income=100000.0,
            total_monthly_spend=3000.0,
            category_spending=json.dumps({
                'dining': 500,
                'travel': 800,
                'groceries': 600,
                'gas': 300,
                'other': 800
            }),
            session_id='test-session-duplicate-check'
        )
        db.session.add(profile)
        db.session.commit()
        
        # Generate first recommendation
        recommendation1 = RecommendationService.generate_recommendation(
            session_id='test-session-duplicate-check',
            profile_id=profile.id
        )
        
        # Verify first recommendation was created
        self.assertIsNotNone(recommendation1)
        self.assertIsNotNone(recommendation1.recommendation_id)
        first_rec_id = recommendation1.recommendation_id
        first_db_id = recommendation1.id
        
        # Generate second recommendation with same profile (should return existing one)
        recommendation2 = RecommendationService.generate_recommendation(
            session_id='test-session-duplicate-check',
            profile_id=profile.id
        )
        
        # Verify second call returned the same recommendation
        self.assertIsNotNone(recommendation2)
        self.assertEqual(recommendation1.recommendation_id, recommendation2.recommendation_id,
                        "Both recommendations should have the same deterministic ID")
        self.assertEqual(recommendation1.id, recommendation2.id,
                        "Both calls should return the same database record")
        
        # Verify no UNIQUE constraint violation occurred (test passes if we get here)
        self.assertEqual(first_rec_id, recommendation2.recommendation_id)
        self.assertEqual(first_db_id, recommendation2.id)

    def test_category_exclusivity_no_double_counting(self):
        """Test that category rewards are not double-counted across multiple cards.
        
        This is a critical test to ensure that when multiple cards offer rewards
        for the same category, only the card with the highest rate is used for
        that category's value calculation.
        """
        # Mock spending profile
        class MockProfile:
            def __init__(self):
                self.max_cards = 3
                self.max_annual_fees = 500
                self.total_monthly_spend = 2000
                
            def get_category_spending(self):
                return {
                    'dining': 500,
                    'travel': 300,
                    'gas': 200,
                    'groceries': 400,
                    'other': 600
                }

        # Mock cards with different rates for same categories
        class MockCard:
            def __init__(self, card_id, name, dining_rate, travel_rate, base_rate, annual_fee):
                self.id = card_id
                self.name = name
                self.dining_reward_rate = dining_rate
                self.travel_reward_rate = travel_rate
                self.gas_reward_rate = 0
                self.grocery_reward_rate = 0
                self.entertainment_reward_rate = 0
                self.base_reward_rate = base_rate
                self.annual_fee = annual_fee
                self.signup_bonus_value = 0
                self.signup_bonus_min_spend = 0
                self.signup_bonus_time_limit = 3

        profile = MockProfile()
        
        # Card A: 3% dining, 2% travel, 1% base, $95 annual fee
        card_a = MockCard(1, 'Card A (3% dining)', 3.0, 2.0, 1.0, 95)
        
        # Card B: 1% everything, no annual fee
        card_b = MockCard(2, 'Card B (1% everything)', 1.0, 1.0, 1.0, 0)
        
        # Calculate individual card values
        value_a = RecommendationEngine.calculate_card_value(card_a, profile)
        value_b = RecommendationEngine.calculate_card_value(card_b, profile)
        
        # Verify individual card calculations
        self.assertEqual(value_a['category_values']['dining'], 15.0)  # 500 * 0.03
        self.assertEqual(value_b['category_values']['dining'], 5.0)   # 500 * 0.01
        
        # Test combination value calculation (should use max for each category)
        cards = [value_a, value_b]
        total_value = RecommendationEngine.calculate_total_combination_value(
            cards, 
            profile.get_category_spending()
        )
        
        # Manual calculation of expected value:
        # Dining: max(500*0.03, 500*0.01) = 15 (Card A wins)
        # Travel: max(300*0.02, 300*0.01) = 6 (Card A wins)  
        # Gas: max(200*0.01, 200*0.01) = 2 (tie, either card)
        # Groceries: max(400*0.01, 400*0.01) = 4 (tie, either card)
        # Other: max(600*0.01, 600*0.01) = 6 (tie, either card)
        # Total monthly: 15+6+2+4+6 = 33
        # Annual category value: 33*12 = 396
        # Total value: 396 + 0 (signup bonuses) - 95 (Card A fee) - 0 (Card B fee) = 301
        
        expected_monthly = (500*0.03) + (300*0.02) + (200*0.01) + (400*0.01) + (600*0.01)
        expected_annual = expected_monthly * 12
        expected_total = expected_annual - 95  # Only Card A has annual fee
        
        self.assertEqual(expected_monthly, 33.0)
        self.assertEqual(expected_annual, 396.0)
        self.assertEqual(expected_total, 301.0)
        self.assertEqual(total_value, expected_total)

    def test_single_card_value_calculation(self):
        """Test that single card value calculation works correctly."""
        class MockProfile:
            def __init__(self):
                self.total_monthly_spend = 1000
                
            def get_category_spending(self):
                return {
                    'dining': 300,
                    'travel': 200,
                    'other': 500
                }

        class MockCard:
            def __init__(self):
                self.id = 1
                self.name = 'Test Card'
                self.dining_reward_rate = 2.0
                self.travel_reward_rate = 1.5
                self.gas_reward_rate = 0
                self.grocery_reward_rate = 0
                self.entertainment_reward_rate = 0
                self.base_reward_rate = 1.0
                self.annual_fee = 50
                self.signup_bonus_value = 0  # No signup bonus to avoid complex calculation
                self.signup_bonus_min_spend = 0
                self.signup_bonus_time_limit = 3

        profile = MockProfile()
        card = MockCard()
        
        result = RecommendationEngine.calculate_card_value(card, profile)
        
        # Expected calculations:
        # Dining: 300 * 0.02 = 6/month
        # Travel: 200 * 0.015 = 3/month  
        # Other: 500 * 0.01 = 5/month
        # Total monthly: 14
        # Annual: 14 * 12 = 168
        # No signup bonus
        # Net value: 168 - 50 = 118
        
        self.assertEqual(result['category_values']['dining'], 6.0)
        self.assertEqual(result['category_values']['travel'], 3.0)
        self.assertEqual(result['category_values']['other'], 5.0)
        self.assertEqual(result['monthly_value'], 14.0)
        self.assertEqual(result['annual_value'], 168.0)
        self.assertEqual(result['signup_bonus_value'], 0.0)
        self.assertEqual(result['net_value'], 118.0)


if __name__ == '__main__':
    unittest.main() 
import unittest
from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
import json

class ModelsTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_model(self):
        """Test User model."""
        user = User(username='test_user', email='test@example.com', password='password')
        db.session.add(user)
        db.session.commit()
        
        # Test retrieval
        retrieved_user = User.query.filter_by(username='test_user').first()
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.email, 'test@example.com')
        self.assertTrue(retrieved_user.check_password('password'))
    
    def test_user_profile_model(self):
        """Test UserProfile model."""
        user = User(username='test_user', email='test@example.com', password='password')
        db.session.add(user)
        db.session.commit()
        
        profile = UserProfile(
            user_id=user.id,
            name='Test Profile',
            credit_score=750,
            income=100000.0,
            total_monthly_spend=5000.0,
            category_spending='{"dining": 500, "travel": 1000, "groceries": 800, "gas": 200, "entertainment": 300, "other": 2200}'
        )
        db.session.add(profile)
        db.session.commit()
        
        # Test retrieval
        retrieved_profile = UserProfile.query.filter_by(name='Test Profile').first()
        self.assertIsNotNone(retrieved_profile)
        self.assertEqual(retrieved_profile.user_id, user.id)
        
        # Test category spending
        category_spending = retrieved_profile.get_category_spending()
        self.assertEqual(category_spending['dining'], 500)
        self.assertEqual(category_spending['travel'], 1000)
    
    def test_credit_card_model(self):
        """Test CreditCard model."""
        card = CreditCard(
            name='Test Card',
            issuer='Test Bank',
            annual_fee=95.0,
            point_value=0.01,
            reward_categories=json.dumps([
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 2.0}
            ]),
            signup_bonus_value=500.0
        )
        db.session.add(card)
        db.session.commit()
        
        # Test retrieval
        retrieved_card = CreditCard.query.filter_by(name='Test Card').first()
        self.assertIsNotNone(retrieved_card)
        self.assertEqual(retrieved_card.issuer, 'Test Bank')
        
        # Test new reward system methods
        self.assertEqual(retrieved_card.base_reward_rate, 1.0)  # Default base rate
        self.assertEqual(retrieved_card.dining_reward_rate, 1.0)  # No specific dining rate set
        self.assertEqual(retrieved_card.travel_reward_rate, 1.0)  # No specific travel rate set
        
        # Test reward calculation methods
        category_spending = {'dining': 500, 'travel': 300}
        monthly_value = retrieved_card.calculate_monthly_value(category_spending)
        self.assertIsInstance(monthly_value, dict)
        self.assertIn('total', monthly_value)
        self.assertIn('by_category', monthly_value)
    
    def test_recommendation_model(self):
        """Test Recommendation model."""
        user = User(username='test_user', email='test@example.com', password='password')
        db.session.add(user)
        db.session.commit()
        
        profile = UserProfile(
            user_id=user.id,
            name='Test Profile',
            credit_score=750,
            income=100000.0,
            total_monthly_spend=5000.0,
            category_spending='{"dining": 500, "travel": 1000, "groceries": 800, "gas": 200, "entertainment": 300, "other": 2200}'
        )
        db.session.add(profile)
        db.session.commit()
        
        # Create a recommendation
        recommendation = Recommendation(
            user_id=user.id,
            user_profile_id=profile.id,
            _spending_profile='{"dining": 500, "travel": 1000, "groceries": 800}',
            _card_preferences='{}',
            _recommended_sequence='[1, 2, 3]',
            _card_details='{"1": {"annual_value": 500}, "2": {"annual_value": 300}, "3": {"annual_value": 200}}',
            total_value=1000.0,
            total_annual_fees=95.0,
            _per_month_value='[83.33, 166.67, 250.0, 333.33, 416.67, 500.0, 583.33, 666.67, 750.0, 833.33, 916.67, 1000.0]',
            card_count=3
        )
        db.session.add(recommendation)
        db.session.commit()
        
        # Test retrieval
        retrieved_recommendation = Recommendation.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(retrieved_recommendation)
        self.assertEqual(retrieved_recommendation.user_profile_id, profile.id)
        
        # Test JSON properties
        self.assertEqual(len(retrieved_recommendation.recommended_sequence), 3)
        self.assertEqual(retrieved_recommendation.card_details['1']['annual_value'], 500)
        self.assertEqual(len(retrieved_recommendation.per_month_value), 12)

if __name__ == '__main__':
    unittest.main() 
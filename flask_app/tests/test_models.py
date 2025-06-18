import unittest
from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from app.models import CardIssuer
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
        """Test CreditCard model creation and methods."""
        issuer = CardIssuer(name='Test Bank')
        db.session.add(issuer)
        db.session.commit()
        
        card = CreditCard(
            name='Test Card',
            issuer_id=issuer.id,
            annual_fee=95.0,
            reward_type='cash_back',
            reward_categories='[]'  # Empty JSON array for the deprecated field
        )
        db.session.add(card)
        db.session.commit()
        
        self.assertEqual(card.name, 'Test Card')
        self.assertEqual(card.annual_fee, 95.0)
        self.assertEqual(card.reward_type, 'cash_back')
        self.assertEqual(card.get_reward_type_display_name(), 'Cash Back')
        
        # Test other reward types
        card.reward_type = 'points'
        self.assertEqual(card.get_reward_type_display_name(), 'Points')
        
        card.reward_type = 'miles'
        self.assertEqual(card.get_reward_type_display_name(), 'Miles')
        
        card.reward_type = 'hotel'
        self.assertEqual(card.get_reward_type_display_name(), 'Hotel')
        
        # Test unknown reward type
        card.reward_type = 'unknown_type'
        self.assertEqual(card.get_reward_type_display_name(), 'Unknown Type')
    
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
            card_count=3,
            recommendation_id="test-recommendation-id"
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
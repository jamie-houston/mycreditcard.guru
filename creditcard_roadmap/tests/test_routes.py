import unittest
from flask import url_for
from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
import json

class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test client
        self.client = self.app.test_client(use_cookies=True)
        
        # Create test user
        self.user = User(username='test_user', email='test@example.com', password='password')
        db.session.add(self.user)
        
        # Create test profile
        self.profile = UserProfile(
            user_id=1,
            name='Test Profile',
            credit_score=750,
            income=100000.0,
            total_monthly_spend=5000.0,
            category_spending='{"dining": 500, "travel": 1000, "groceries": 800, "gas": 200, "entertainment": 300, "other": 2200}'
        )
        db.session.add(self.profile)
        
        # Create test cards
        card1 = CreditCard(
            name='Test Card 1',
            issuer='Test Bank',
            annual_fee=95.0,
            point_value=0.01,
            reward_categories=json.dumps([
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 2.0}
            ]),
            signup_bonus_value=500.0
        )
        card2 = CreditCard(
            name='Test Card 2',
            issuer='Other Bank',
            annual_fee=0.0,
            point_value=0.01,
            reward_categories=json.dumps([
                {"category": "groceries", "rate": 2.0},
                {"category": "gas", "rate": 2.0}
            ]),
            signup_bonus_value=200.0
        )
        db.session.add(card1)
        db.session.add(card2)
        
        # Create test recommendation
        self.recommendation = Recommendation(
            user_id=1,
            profile_id=1,
            _spending_profile='{"dining": 500, "travel": 1000, "groceries": 800}',
            _card_preferences='{}',
            _recommended_sequence='[1, 2]',
            _card_details='{"1": {"annual_value": 500}, "2": {"annual_value": 300}}',
            total_value=800.0,
            total_annual_fees=95.0,
            _per_month_value='[66.67, 133.33, 200.0, 266.67, 333.33, 400.0, 466.67, 533.33, 600.0, 666.67, 733.33, 800.0]',
            card_count=2
        )
        db.session.add(self.recommendation)
        
        db.session.commit()
        
        # Log in the test user
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
                sess['_fresh'] = True
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_index_page(self):
        """Test index page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_recommendations_list(self):
        """Test recommendations list page."""
        response = self.client.get('/recommendations/')
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_view(self):
        """Test recommendation view page."""
        response = self.client.get(f'/recommendations/view/{self.recommendation.id}')
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_create(self):
        """Test recommendation create endpoint."""
        response = self.client.get(f'/recommendations/create/{self.profile.id}')
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Follow redirect
        response = self.client.get(response.location)
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_delete(self):
        """Test recommendation delete endpoint."""
        response = self.client.get(f'/recommendations/delete/{self.recommendation.id}')
        self.assertEqual(response.status_code, 302)  # Redirect after deletion
        
        # Check that recommendation was deleted
        recommendation = Recommendation.query.get(self.recommendation.id)
        self.assertIsNone(recommendation)

if __name__ == '__main__':
    unittest.main() 
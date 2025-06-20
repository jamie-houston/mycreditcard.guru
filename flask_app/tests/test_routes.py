import unittest
from flask import url_for
from app import create_app, db
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from app.models import CardIssuer, Category
import json

class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test client
        self.client = self.app.test_client(use_cookies=True)
        
        # Create test user with unique username
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        self.user = User(username=f'test_user_{unique_id}', email=f'test_{unique_id}@example.com', password='password')
        db.session.add(self.user)
        db.session.commit()  # Commit to get the user ID
        
        # Create test profile
        self.profile = UserProfile(
            user_id=self.user.id,
            name='Test Profile',
            credit_score=750,
            income=100000.0,
            total_monthly_spend=5000.0,
            category_spending='{"dining": 500, "travel": 1000, "groceries": 800, "gas": 200, "entertainment": 300, "other": 2200}'
        )
        db.session.add(self.profile)
        db.session.commit()  # Commit to get the profile ID
        
        # Create test issuers with unique names
        self.test_issuer = CardIssuer(name=f'Test Bank {unique_id}')
        self.other_issuer = CardIssuer(name=f'Other Bank {unique_id}')
        db.session.add(self.test_issuer)
        db.session.add(self.other_issuer)
        db.session.commit()
        
        # Create test categories (or get existing ones)
        category_names = ['dining', 'travel', 'groceries', 'gas', 'other']
        for cat_name in category_names:
            existing_category = Category.query.filter_by(name=cat_name).first()
            if not existing_category:
                category = Category(name=cat_name, display_name=cat_name.title())
                db.session.add(category)
        db.session.commit()
        
        # Create test cards
        card1 = self.create_card_with_rewards(
            name='Test Card 1',
            issuer_id=self.test_issuer.id,
            annual_fee=95.0,
            reward_categories=[
                {"category": "dining", "rate": 3.0},
                {"category": "travel", "rate": 2.0}
            ],
            signup_bonus={"amount": 500.0}
        )
        card2 = self.create_card_with_rewards(
            name='Test Card 2',
            issuer_id=self.other_issuer.id,
            annual_fee=0.0,
            reward_categories=[
                {"category": "groceries", "rate": 2.0},
                {"category": "gas", "rate": 2.0}
            ],
            signup_bonus={"amount": 200.0}
        )
        db.session.add(card1)
        db.session.add(card2)
        db.session.commit()  # Commit to get the card IDs
        
        # Create a recommendation
        self.recommendation = Recommendation(
            user_id=self.user.id,
            user_profile_id=self.profile.id,
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
        db.session.add(self.recommendation)
        db.session.commit()
        
        # Log in the test user
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
    
    def create_card_with_rewards(self, name, issuer_id, annual_fee, reward_categories, signup_bonus=None):
        """Helper method to create a credit card with reward categories."""
        card = CreditCard(
            name=name,
            issuer_id=issuer_id,
            annual_fee=annual_fee,
            reward_value_multiplier=1.0,
            signup_bonus=json.dumps(signup_bonus or {"amount": 0}),
            is_active=True
        )
        db.session.add(card)
        db.session.flush()  # Get the card ID
        
        # Add reward categories using the add_reward_category method
        for reward in reward_categories:
            card.add_reward_category(
                category_name=reward["category"],
                reward_percent=reward["rate"]
            )
        
        return card
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_index_page(self):
        """Test index page redirects authenticated users to profile."""
        response = self.client.get('/')
        # Authenticated users should be redirected to profile
        self.assertEqual(response.status_code, 302)
        with self.app.test_request_context():
            expected_url = url_for('user_data.profile')
            self.assertIn(expected_url, response.location)
    
    def test_recommendations_list(self):
        """Test recommendations list page."""
        # Log in the user via session
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
        
        response = self.client.get('/recommendations/')
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_view(self):
        """Test recommendation view page."""
        # Log in the user via session
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
        
        # Use the shareable recommendation_id, not the database ID
        response = self.client.get(f'/recommendations/view/{self.recommendation.recommendation_id}')
        if response.status_code == 302:
            response = self.client.get(response.location)
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_create(self):
        """Test recommendation create endpoint."""
        # Log in the user via session
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
        
        response = self.client.get(f'/recommendations/create/{self.profile.id}')
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Follow redirect
        response = self.client.get(response.location)
        self.assertEqual(response.status_code, 200)
    
    def test_recommendation_delete(self):
        """Test recommendation delete endpoint."""
        # Log in the user via session
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
        
        # Use the shareable recommendation_id, not the database ID
        response = self.client.post(f'/recommendations/delete/{self.recommendation.recommendation_id}')
        self.assertEqual(response.status_code, 302)  # Redirect after deletion
        
        # Check that recommendation was deleted
        recommendation = db.session.get(Recommendation, self.recommendation.id)
        self.assertIsNone(recommendation)

if __name__ == '__main__':
    unittest.main() 
import unittest
from flask import url_for
from flask_login import login_user
from app import create_app, db
from app.models.user import User


class LandingPageTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test client
        self.client = self.app.test_client(use_cookies=True)
        
        # Create test user
        self.user = User(username='test_user', email='test@example.com', password='password')
        db.session.add(self.user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_landing_page_redirect_for_authenticated_user(self):
        """Test that authenticated users are redirected to profile page from landing page."""
        # Log in the user via session using Flask-Login's session key
        with self.client as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(self.user.id)  # Flask-Login uses _user_id and expects string
                sess['_fresh'] = True
        
        # Access the landing page
        response = self.client.get('/')
        
        # Should redirect to profile page
        self.assertEqual(response.status_code, 302)
        with self.app.test_request_context():
            expected_url = url_for('user_data.profile')
            self.assertIn(expected_url, response.location)

    def test_landing_page_shows_welcome_for_anonymous_user(self):
        """Test that anonymous users see the welcome page."""
        response = self.client.get('/')
        
        # Should show the welcome page, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to Credit Card Roadmap', response.data)
        self.assertIn(b'Find the perfect credit card strategy', response.data)

    def test_landing_page_has_get_started_button_for_anonymous(self):
        """Test that anonymous users see the Get Started button."""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Get Started', response.data)
        # The button should link to the profile page
        self.assertIn(b'href="/profile/profile"', response.data)


if __name__ == '__main__':
    unittest.main() 
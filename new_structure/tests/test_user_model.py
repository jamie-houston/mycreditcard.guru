import unittest
from app import create_app, db
from app.models.user import User
import os
import tempfile


class UserModelTestCase(unittest.TestCase):
    """Test case for the User model."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Configure the application for testing
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        }
        
        # Create and configure the app
        self.app = create_app('testing')
        self.app.config.update(test_config)
        
        # Establish application context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Set up the database
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_password_hashing(self):
        """Test password hashing works correctly."""
        u = User(username='test', email='test@example.com', password='cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))
    
    def test_user_creation(self):
        """Test user creation and attributes."""
        u = User(username='test', email='test@example.com', password='cat')
        db.session.add(u)
        db.session.commit()
        
        # Fetch user from database
        user = User.query.filter_by(username='test').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(hasattr(user, 'password_hash'))
        self.assertFalse(hasattr(user, 'password'))
    
    def test_admin_role(self):
        """Test admin role assignment."""
        u1 = User(username='regular', email='regular@example.com', password='cat')
        u2 = User(username='admin', email='admin@example.com', password='cat', is_admin=True)
        
        db.session.add_all([u1, u2])
        db.session.commit()
        
        self.assertFalse(u1.is_admin)
        self.assertTrue(u2.is_admin)


if __name__ == '__main__':
    unittest.main() 
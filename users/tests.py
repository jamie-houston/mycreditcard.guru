from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import UserProfile, UserPreferences
from cards.models import CreditCard, SpendingCategory


class UserModelTests(TestCase):
    """Test suite for user models and basic functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_user_profile_creation(self):
        """Test UserProfile model creation and string representation"""
        profile = UserProfile.objects.create(
            user=self.user,
            max_annual_fee=Decimal("150.00")
        )
        self.assertEqual(profile.max_annual_fee, Decimal("150.00"))
        self.assertEqual(str(profile), "test@example.com's Profile")
    
    def test_user_preferences_creation(self):
        """Test UserPreferences model creation"""
        preferences = UserPreferences.objects.create(
            user=self.user,
            email_notifications=True,
            theme='dark',
            default_max_recommendations=3
        )
        self.assertTrue(preferences.email_notifications)
        self.assertEqual(preferences.theme, 'dark')
        self.assertEqual(preferences.default_max_recommendations, 3)
        self.assertEqual(str(preferences), "test@example.com's Preferences")


class UserAPITests(TestCase):
    """Basic API endpoint tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_user_data_endpoint_requires_auth(self):
        """Test that user data endpoint requires authentication"""
        response = self.client.get('/api/users/data/')
        # Endpoint returns 403 (Forbidden) instead of 401 (Unauthorized) when not authenticated
        self.assertEqual(response.status_code, 403)
    
    def test_user_profile_endpoint_with_auth(self):
        """Test user profile endpoint with authentication"""
        self.client.force_login(self.user)
        response = self.client.get('/api/users/profile/')
        self.assertEqual(response.status_code, 200)
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Roadmap, RoadmapFilter, RoadmapRecommendation, RoadmapCalculation
from cards.models import UserSpendingProfile, CreditCard, Issuer, RewardType


class RoadmapModelTests(TestCase):
    """Test suite for roadmap models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        
    def test_roadmap_creation(self):
        """Test Roadmap model creation"""
        roadmap = Roadmap.objects.create(
            profile=self.profile,
            name="Test Roadmap"
        )
        self.assertEqual(roadmap.name, "Test Roadmap")
        self.assertEqual(str(roadmap), f"{self.profile} - Test Roadmap")
    
    def test_roadmap_filter_creation(self):
        """Test RoadmapFilter model creation"""
        roadmap_filter = RoadmapFilter.objects.create(
            name="High Spending Filter",
            filter_type="high_spending"
        )
        self.assertEqual(roadmap_filter.name, "High Spending Filter")
        self.assertEqual(str(roadmap_filter), "High Spending Filter (high_spending)")


class RoadmapAPITests(TestCase):
    """Basic roadmap API tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_roadmap_list_endpoint_anonymous_access(self):
        """Test that roadmap endpoint works for anonymous users (returns empty results)"""
        response = self.client.get('/api/roadmaps/')
        self.assertEqual(response.status_code, 200)
        # Should return paginated empty results for anonymous users with no session data
        data = response.json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
    
    def test_roadmap_list_with_auth(self):
        """Test roadmap list with authentication"""
        self.client.force_login(self.user)
        response = self.client.get('/api/roadmaps/')
        self.assertEqual(response.status_code, 200)
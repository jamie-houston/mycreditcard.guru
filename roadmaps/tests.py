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

    def test_quick_recommendation_rejects_unknown_strategy(self):
        """A typo'd strategy key through the API must 400, not run the default"""
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {'strategy': 'simple_cashback'},  # missing underscore
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('strategy', response.json())


class StrategyUITests(TestCase):
    """S2: effort-tolerance question + advanced strategy picker on the roadmap page"""

    def setUp(self):
        # base.html renders a Google sign-in link; allauth needs a SocialApp
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        app = SocialApp.objects.create(
            provider='google', name='Google', client_id='test', secret='test'
        )
        app.sites.add(Site.objects.get_current())

    def test_ui_presets_shape(self):
        """ui_presets exposes everything the template needs, ordered low->high effort"""
        from .strategies import ui_presets, STRATEGIES
        presets = ui_presets()
        self.assertEqual([p['key'] for p in presets], list(STRATEGIES))
        for preset in presets:
            for field in ('key', 'name', 'effort_label', 'description',
                          'max_recommendations', 'pool_label'):
                self.assertIn(field, preset)
        by_key = {p['key']: p for p in presets}
        self.assertEqual(by_key['simple_cash_back']['pool_label'], 'Cashback')
        self.assertEqual(by_key['travel_points']['pool_label'], 'Points / Miles / Hotel')
        self.assertEqual(by_key['maximizer']['pool_label'], 'All reward types')

    def test_roadmap_page_renders_strategy_section(self):
        """The effort question and all presets render; picker offers a no-strategy option"""
        from .strategies import STRATEGIES
        response = self.client.get('/roadmap/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('How much effort do you want to put in?', content)
        self.assertIn('No strategy', content)
        self.assertIn('id="strategiesData"', content)  # json_script feed for the JS
        for strategy in STRATEGIES.values():
            self.assertIn(strategy['effort_label'], content)
            self.assertIn(f'effort-{strategy["key"]}', content)

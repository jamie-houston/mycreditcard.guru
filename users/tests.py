from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import UserProfile, UserPreferences
from cards.models import (
    CreditCard, SpendingCategory, Issuer, RewardType, UserCard,
    UserSpendingProfile, ProfileEntity
)


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


class SoftCloseSurvivesBulkSaveTests(TestCase):
    """Regression test: /api/cards/user-cards/toggle/ (the Phase F5
    consolidated home for card-ownership toggling, formerly
    /api/users/cards/toggle/) soft-closes a card via closed_date (never
    hard-deletes, to preserve eligibility history like Chase 5/24 and
    Amex-lifetime). The bulk /api/users/data/ save (which index.html's
    saveCurrentData() calls before every roadmap generation) used to
    hard-delete any UserCard not in its posted card-id list — including
    soft-closed ones, since to_representation() already excludes them from
    that list. That silently destroyed the closed_date history the very
    next time a roadmap was generated."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='closer', email='closer@example.com', password='x')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Closable Card', slug='closable-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def test_soft_closed_card_survives_bulk_data_save(self):
        from datetime import date
        user_card = UserCard.objects.create(
            user=self.user, card=self.card, opened_date=date(2024, 1, 1))

        toggle_response = self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': 'remove'},
            content_type='application/json')
        self.assertEqual(toggle_response.status_code, 200)
        user_card.refresh_from_db()
        self.assertIsNotNone(user_card.closed_date)

        # Bulk save posts an empty active-card list (mirrors saveCurrentData())
        save_response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(save_response.status_code, 200)

        # The closed card row must still exist with its closed_date intact
        self.assertTrue(UserCard.objects.filter(id=user_card.id).exists())
        user_card.refresh_from_db()
        self.assertIsNotNone(user_card.closed_date)

    def test_bulk_save_still_removes_active_cards_not_in_list(self):
        from datetime import date
        UserCard.objects.create(
            user=self.user, card=self.card, opened_date=date(2024, 1, 1))

        response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserCard.objects.filter(user=self.user).exists())


class HouseholdBulkSaveOwnerScopingTests(TestCase):
    """Phase K1: the bulk /api/users/data/ save manages the flat,
    household-wide card list index.html's browse page shows, but its
    delete guard and add-loop must not touch or duplicate a NON-primary
    entity's cards — see users/serializers.py UserDataSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(username='household', password='x')
        self.profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        self.primary = self.profile.primary_entity()
        self.sam = ProfileEntity.objects.create(profile=self.profile, name='Sam')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Household Card', slug='household-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.other_card = CreditCard.objects.create(
            name='Other Card', slug='other-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def test_sams_active_card_survives_empty_bulk_save(self):
        sam_card = UserCard.objects.create(user=self.user, card=self.card, owner=self.sam)

        response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.assertTrue(UserCard.objects.filter(id=sam_card.id).exists())
        sam_card.refresh_from_db()
        self.assertIsNone(sam_card.closed_date)

    def test_sams_card_id_in_posted_list_does_not_duplicate_onto_primary(self):
        """The flat list from to_representation() is household-wide, so
        Sam's card id can appear in a bulk save posted by the primary's own
        browser session (e.g. after loadCurrentData() round-trips it back).
        It must not spawn a second, primary-owned row."""
        sam_card = UserCard.objects.create(user=self.user, card=self.card, owner=self.sam)

        response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [self.card.id], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            UserCard.objects.filter(user=self.user, card=self.card).count(), 1)
        sam_card.refresh_from_db()
        self.assertEqual(sam_card.owner, self.sam)

    def test_primarys_active_card_removed_when_absent_from_list(self):
        primary_card = UserCard.objects.create(
            user=self.user, card=self.other_card, owner=self.primary)

        response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # This path hard-deletes (existing behavior, unchanged by Phase K)
        # — unlike remove_user_card/toggle_user_card, which soft-close.
        self.assertFalse(UserCard.objects.filter(id=primary_card.id).exists())

    def test_new_card_in_list_created_for_primary(self):
        response = self.client.post(
            '/api/users/data/',
            {'spending': {}, 'cards': [self.other_card.id], 'preferences': {}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        user_card = UserCard.objects.get(user=self.user, card=self.other_card)
        self.assertEqual(user_card.owner, self.primary)
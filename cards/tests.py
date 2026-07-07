from django.test import TestCase
from django.contrib.auth.models import User

from .models import (
    SpendingCategory, SpendingCredit, UserSpendingProfile,
    UserSpendingCreditPreference
)


class CreditPreferencesAPITests(TestCase):
    def setUp(self):
        self.category = SpendingCategory.objects.create(name='Travel', slug='travel')
        self.lounge = SpendingCredit.objects.create(
            name='Airport Lounge', slug='airport_lounge',
            display_name='Airport Lounge Access', category=self.category,
            stackable=False)
        self.uber_eats = SpendingCredit.objects.create(
            name='Uber Eats', slug='uber_eats',
            display_name='Uber Eats Credit', category=self.category,
            stackable=True)

    def test_get_with_no_profile_returns_empty(self):
        response = self.client.get('/api/cards/credit-preferences/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'preferences': {}})

    def test_put_then_get_auth_round_trip(self):
        user = User.objects.create_user(username='u', password='x')
        self.client.force_login(user)

        response = self.client.put(
            '/api/cards/credit-preferences/',
            {'preferences': {'airport_lounge': False, 'uber_eats': True}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preferences'], {
            'airport_lounge': False, 'uber_eats': True,
        })

        # Explicit False persisted as a real row, not treated as absent.
        profile = UserSpendingProfile.objects.get(user=user)
        pref = UserSpendingCreditPreference.objects.get(
            profile=profile, spending_credit=self.lounge)
        self.assertFalse(pref.values_credit)

        get_response = self.client.get('/api/cards/credit-preferences/')
        self.assertEqual(get_response.json()['preferences'], {
            'airport_lounge': False, 'uber_eats': True,
        })

    def test_put_creates_session_for_anon_user(self):
        response = self.client.put(
            '/api/cards/credit-preferences/',
            {'preferences': {'uber_eats': True}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.session.session_key)

        profile = UserSpendingProfile.objects.get(
            session_key=self.client.session.session_key)
        self.assertTrue(UserSpendingCreditPreference.objects.filter(
            profile=profile, spending_credit=self.uber_eats,
            values_credit=True).exists())

        get_response = self.client.get('/api/cards/credit-preferences/')
        self.assertEqual(get_response.json(), {'preferences': {'uber_eats': True}})

    def test_put_unknown_slug_ignored(self):
        response = self.client.put(
            '/api/cards/credit-preferences/',
            {'preferences': {'not_a_real_credit': True}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'preferences': {}})

    def test_put_requires_preferences_object(self):
        response = self.client.put(
            '/api/cards/credit-preferences/',
            {'preferences': ['not', 'a', 'dict']},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

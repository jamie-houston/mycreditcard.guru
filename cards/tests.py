from django.test import TestCase
from django.contrib.auth.models import User

from .models import (
    SpendingCategory, SpendingCredit, UserSpendingProfile,
    UserSpendingCreditPreference, CreditCard, Issuer, RewardType, UserCard
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


class UserCardOwnershipSoftCloseTests(TestCase):
    """Phase F2: cards/user-cards/<id>/delete/ (remove_user_card) used to
    hard-delete the UserCard row, erasing eligibility-relevant history
    (Chase 5/24, BofA 2/3/4, Amex lifetime, Citi 48-month all evaluate
    against closed cards' dates — see roadmaps/eligibility.py). It must
    soft-close via closed_date instead. Also covers the re-add round trip:
    /user-cards/add/ must reopen a previously soft-closed row rather than
    erroring on the (user, card, owner) unique constraint or leaving it
    closed."""

    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='x')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Ownable Card', slug='ownable-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def test_remove_soft_closes_instead_of_deleting(self):
        from datetime import date
        user_card = UserCard.objects.create(
            user=self.user, card=self.card, opened_date=date(2024, 1, 1))

        response = self.client.delete(f'/api/cards/user-cards/{user_card.id}/delete/')
        self.assertEqual(response.status_code, 200)

        self.assertTrue(UserCard.objects.filter(id=user_card.id).exists())
        user_card.refresh_from_db()
        self.assertIsNotNone(user_card.closed_date)

    def test_readd_after_soft_close_reopens_same_row(self):
        from datetime import date
        user_card = UserCard.objects.create(
            user=self.user, card=self.card, opened_date=date(2024, 1, 1))

        self.client.delete(f'/api/cards/user-cards/{user_card.id}/delete/')
        user_card.refresh_from_db()
        self.assertIsNotNone(user_card.closed_date)

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['created'])

        # Must reopen the SAME row (unique constraint), not create a duplicate
        self.assertEqual(UserCard.objects.filter(user=self.user, card=self.card).count(), 1)
        user_card.refresh_from_db()
        self.assertEqual(user_card.id, UserCard.objects.get(user=self.user, card=self.card).id)
        self.assertIsNone(user_card.closed_date)


class UserCardToggleEndpointTests(TestCase):
    """Phase F5: cards/user-cards/toggle/ is the consolidated replacement
    for the retired users/cards/toggle/ — single add/remove ergonomics for
    callers (base.html's ownership toggle, roadmap-results.js's "Remove
    from my cards") that don't want a two-step add-then-delete flow. Must
    soft-close on remove and reopen (never duplicate) on re-add, same as
    the /user-cards/add/ + /delete/ pair it replaces."""

    def setUp(self):
        self.user = User.objects.create_user(username='toggler', password='x')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Togglable Card', slug='togglable-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def _toggle(self, action, **extra):
        return self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': action, **extra},
            content_type='application/json')

    def test_add_creates_active_card(self):
        response = self._toggle('add', nickname='My Card')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        user_card = UserCard.objects.get(user=self.user, card=self.card)
        self.assertIsNone(user_card.closed_date)
        self.assertEqual(user_card.nickname, 'My Card')

    def test_remove_soft_closes(self):
        UserCard.objects.create(user=self.user, card=self.card)

        response = self._toggle('remove')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        user_card = UserCard.objects.get(user=self.user, card=self.card)
        self.assertIsNotNone(user_card.closed_date)

    def test_add_after_remove_reopens_same_row_no_duplicate(self):
        user_card = UserCard.objects.create(user=self.user, card=self.card)
        self._toggle('remove')
        user_card.refresh_from_db()
        self.assertIsNotNone(user_card.closed_date)

        response = self._toggle('add')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(UserCard.objects.filter(user=self.user, card=self.card).count(), 1)
        user_card.refresh_from_db()
        self.assertIsNone(user_card.closed_date)

    def test_requires_auth(self):
        self.client.logout()
        response = self._toggle('add')
        self.assertEqual(response.status_code, 403)

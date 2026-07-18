"""Phase K1: ProfileEntity CRUD and owner-aware UserCard ownership.

Multi-player households — see docs/PLAN_PHASE_K_HOUSEHOLDS.md. These tests
cover the inert model/API layer only: the engine still ignores `owner`
until K2b, so nothing here touches recommendation math.
"""
from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User

from .models import (
    CreditCard, Issuer, RewardType, UserCard, UserSpendingProfile,
    ProfileEntity,
)


class ProfileEntityCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='household', first_name='Jamie', password='x')
        self.client.force_login(self.user)

    def test_get_lazily_creates_primary(self):
        self.assertFalse(ProfileEntity.objects.filter(profile__user=self.user).exists())

        response = self.client.get('/api/cards/profile-entities/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]['is_primary'])
        self.assertEqual(data[0]['name'], 'Jamie')

    def test_post_creates_additional_entity(self):
        response = self.client.post(
            '/api/cards/profile-entities/',
            {'name': 'Sam', 'kind': 'personal'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['name'], 'Sam')
        self.assertFalse(data['is_primary'])

        # Primary was auto-created too, alongside the explicit one.
        profile = UserSpendingProfile.objects.get(user=self.user)
        self.assertEqual(profile.entities.count(), 2)

    def test_post_rejects_duplicate_name(self):
        self.client.get('/api/cards/profile-entities/')  # creates primary "Jamie"
        response = self.client.post(
            '/api/cards/profile-entities/',
            {'name': 'Jamie'},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_post_requires_name(self):
        response = self.client.post(
            '/api/cards/profile-entities/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_patch_renames_entity(self):
        profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        entity = profile.primary_entity()

        response = self.client.patch(
            f'/api/cards/profile-entities/{entity.id}/',
            {'name': 'Jamie H.'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        entity.refresh_from_db()
        self.assertEqual(entity.name, 'Jamie H.')

    def test_primary_cannot_be_deleted(self):
        profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        entity = profile.primary_entity()

        response = self.client.delete(f'/api/cards/profile-entities/{entity.id}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(ProfileEntity.objects.filter(id=entity.id).exists())

    def test_non_primary_entity_deletable_when_no_cards(self):
        profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        entity = ProfileEntity.objects.create(profile=profile, name='Sam')

        response = self.client.delete(f'/api/cards/profile-entities/{entity.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProfileEntity.objects.filter(id=entity.id).exists())

    def test_deleting_entity_with_cards_is_protected(self):
        profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        entity = ProfileEntity.objects.create(profile=profile, name='Sam')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        card = CreditCard.objects.create(
            name='Sam Card', slug='sam-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        UserCard.objects.create(user=self.user, card=card, owner=entity)

        response = self.client.delete(f'/api/cards/profile-entities/{entity.id}/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('card', response.json()['error'])
        self.assertTrue(ProfileEntity.objects.filter(id=entity.id).exists())

    def test_cannot_rename_or_delete_another_users_entity(self):
        other = User.objects.create_user(username='intruder', password='x')
        other_profile = UserSpendingProfile.objects.get_or_create(user=other)[0]
        other_entity = other_profile.primary_entity()

        response = self.client.patch(
            f'/api/cards/profile-entities/{other_entity.id}/',
            {'name': 'Hijacked'},
            content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_requires_auth(self):
        self.client.logout()
        response = self.client.get('/api/cards/profile-entities/')
        self.assertEqual(response.status_code, 403)

    def test_deleting_user_cascades_despite_restricted_owner_fk(self):
        """Regression: UserCard.owner uses RESTRICT, not PROTECT. PROTECT
        unconditionally blocks deleting the referenced ProfileEntity even
        when the referencing UserCard is ALSO being deleted in the same
        cascade (e.g. via User -> UserSpendingProfile -> ProfileEntity and
        User -> UserCard both cascading from one User.delete() call) —
        that would make it impossible to ever delete a user account with
        any owned cards. RESTRICT defers to same-batch cascades, so this
        must succeed cleanly."""
        profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        entity = ProfileEntity.objects.create(profile=profile, name='Sam')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        card = CreditCard.objects.create(
            name='Cascade Card', slug='cascade-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        UserCard.objects.create(user=self.user, card=card, owner=entity)

        user_id = self.user.id
        self.user.delete()

        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertFalse(ProfileEntity.objects.filter(id=entity.id).exists())
        self.assertFalse(UserCard.objects.filter(card=card).exists())


class MultiOwnerCardOwnershipTests(TestCase):
    """Two entities in the same household can each hold their own copy of
    the same card — the reason unique_together(user, card) had to be
    relaxed to (user, card, owner)."""

    def setUp(self):
        self.user = User.objects.create_user(username='household2', password='x')
        self.profile = UserSpendingProfile.objects.get_or_create(user=self.user)[0]
        self.primary = self.profile.primary_entity()
        self.sam = ProfileEntity.objects.create(profile=self.profile, name='Sam')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Shared Card', slug='shared-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def test_two_owners_can_each_hold_the_same_card(self):
        UserCard.objects.create(user=self.user, card=self.card, owner=self.primary)
        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id, 'owner': self.sam.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['created'])

        self.assertEqual(
            UserCard.objects.filter(user=self.user, card=self.card).count(), 2)

    def test_add_rejects_owner_from_another_household(self):
        other = User.objects.create_user(username='other', password='x')
        other_profile = UserSpendingProfile.objects.get_or_create(user=other)[0]
        foreign_entity = other_profile.primary_entity()

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id, 'owner': foreign_entity.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_readd_cannot_reassign_owner_to_another_household(self):
        """Regression: add_user_card's re-add branch (existing row found)
        re-validates the posted `owner` through UserCardCreateUpdateSerializer
        — that serializer's validate_owner needs request context to enforce
        the same-household check, or a crafted `owner` in a re-add payload
        could silently reassign the card to a foreign ProfileEntity."""
        other = User.objects.create_user(username='other2', password='x')
        other_profile = UserSpendingProfile.objects.get_or_create(user=other)[0]
        foreign_entity = other_profile.primary_entity()
        existing = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.primary)

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id, 'owner': foreign_entity.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        existing.refresh_from_db()
        self.assertEqual(existing.owner_id, self.primary.id)

    def test_patch_cannot_reassign_owner_to_another_household(self):
        other = User.objects.create_user(username='other3', password='x')
        other_profile = UserSpendingProfile.objects.get_or_create(user=other)[0]
        foreign_entity = other_profile.primary_entity()
        existing = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.primary)

        response = self.client.patch(
            f'/api/cards/user-cards/{existing.id}/',
            {'owner': foreign_entity.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        existing.refresh_from_db()
        self.assertEqual(existing.owner_id, self.primary.id)

    def test_toggle_add_reopens_legacy_null_owner_row_as_primary(self):
        """A pre-Phase-K row (owner=NULL) is the primary's row — re-adding
        via the primary must reopen it, not create a duplicate."""
        legacy = UserCard.objects.create(user=self.user, card=self.card, owner=None)
        legacy.closed_date = date(2024, 6, 1)
        legacy.save(update_fields=['closed_date'])

        response = self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': 'add'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            UserCard.objects.filter(user=self.user, card=self.card).count(), 1)
        legacy.refresh_from_db()
        self.assertIsNone(legacy.closed_date)

    def test_toggle_remove_scoped_by_owner(self):
        primary_row = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.primary)
        sam_row = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.sam)

        response = self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': 'remove', 'owner': self.sam.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        primary_row.refresh_from_db()
        sam_row.refresh_from_db()
        self.assertIsNone(primary_row.closed_date)
        self.assertIsNotNone(sam_row.closed_date)

    def test_toggle_remove_without_owner_prefers_primary_row(self):
        """When the primary holds a copy too, an owner-less remove targets
        THAT row — matching add's default-to-primary behavior — even
        though another entity also holds the card."""
        primary_row = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.primary)
        sam_row = UserCard.objects.create(
            user=self.user, card=self.card, owner=self.sam)

        response = self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': 'remove'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        primary_row.refresh_from_db()
        sam_row.refresh_from_db()
        self.assertIsNotNone(primary_row.closed_date)
        self.assertIsNone(sam_row.closed_date)

    def test_toggle_remove_without_owner_ambiguous_returns_400(self):
        """No primary/NULL-owned row exists, and two non-primary entities
        both hold copies — there's no default to fall back on."""
        jordan = ProfileEntity.objects.create(profile=self.profile, name='Jordan')
        UserCard.objects.create(user=self.user, card=self.card, owner=self.sam)
        UserCard.objects.create(user=self.user, card=self.card, owner=jordan)

        response = self.client.post(
            '/api/cards/user-cards/toggle/',
            {'card_id': self.card.id, 'action': 'remove'},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_serializer_owner_name_resolves_null_to_primary(self):
        legacy = UserCard.objects.create(user=self.user, card=self.card, owner=None)
        response = self.client.get('/api/cards/user-cards/')
        self.assertEqual(response.status_code, 200)
        row = next(r for r in response.json() if r['id'] == legacy.id)
        self.assertEqual(row['owner_name'], self.primary.name)

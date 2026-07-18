"""Phase K1: migration-backfill assertion — every pre-existing UserCard row
gets an owner after 0008_backfill_primary_entities runs.

This repo has no prior precedent for MigrationExecutor-based tests (verified
via grep before writing this), so this is a from-scratch pattern: migrate
the test DB back to just before 0007, insert legacy-shaped rows (a user with
a UserCard and no ProfileEntity — exactly what production looks like
pre-Phase-K), migrate forward through 0008, and assert the backfill did its
job. TransactionTestCase is required — MigrationExecutor issues real
schema/DDL operations that a wrapped-in-a-transaction TestCase would roll
back around.
"""
from django.test import TransactionTestCase
from django.db.migrations.executor import MigrationExecutor
from django.db import connection


class BackfillPrimaryEntitiesMigrationTests(TransactionTestCase):
    def test_every_legacy_usercard_gets_an_owner(self):
        executor = MigrationExecutor(connection)
        app = 'cards'

        # Migrate back to just before the owner field/backfill existed.
        executor.migrate([(app, '0006_cardcredit_offer_type_usercard_bonus_override')])
        executor.loader.build_graph()

        old_apps = executor.loader.project_state(
            [(app, '0006_cardcredit_offer_type_usercard_bonus_override')]
        ).apps
        User = old_apps.get_model('auth', 'User')
        RewardType = old_apps.get_model('cards', 'RewardType')
        Issuer = old_apps.get_model('cards', 'Issuer')
        CreditCard = old_apps.get_model('cards', 'CreditCard')
        UserCard = old_apps.get_model('cards', 'UserCard')
        UserSpendingProfile = old_apps.get_model('cards', 'UserSpendingProfile')

        user = User.objects.create(username='legacy_owner')
        # A user with a profile but no ProfileEntity yet (pre-Phase-K shape).
        UserSpendingProfile.objects.create(user=user)
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        card = CreditCard.objects.create(
            name='Legacy Card', slug='legacy-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        UserCard.objects.create(user=user, card=card, opened_date='2024-01-01')

        # A UserCard owned by a user who has NO profile at all yet — the
        # backfill must get_or_create the profile before creating its entity.
        orphan_user = User.objects.create(username='profileless_owner')
        UserCard.objects.create(user=orphan_user, card=card, opened_date='2024-01-01')

        # Migrate forward through the owner field + backfill.
        executor.loader.build_graph()
        executor.migrate([(app, '0008_backfill_primary_entities')])
        executor.loader.build_graph()

        new_apps = executor.loader.project_state(
            [(app, '0008_backfill_primary_entities')]
        ).apps
        UserCard = new_apps.get_model('cards', 'UserCard')
        ProfileEntity = new_apps.get_model('cards', 'ProfileEntity')
        UserSpendingProfile = new_apps.get_model('cards', 'UserSpendingProfile')

        self.assertFalse(UserCard.objects.filter(owner__isnull=True).exists())

        for username in ('legacy_owner', 'profileless_owner'):
            profile = UserSpendingProfile.objects.get(user__username=username)
            entity = ProfileEntity.objects.get(profile=profile, is_primary=True)
            user_card = UserCard.objects.get(user__username=username)
            self.assertEqual(user_card.owner_id, entity.id)

        # Leave the DB on the latest migration for every other test in the suite.
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

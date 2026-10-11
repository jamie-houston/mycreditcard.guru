from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

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


class UserCardReappliedHistoryTests(TestCase):
    """Story 13: a closed holding and a later re-applied one can coexist as
    two rows under one (user, card, owner) — the partial unique constraint
    only forbids two *open* rows. /user-cards/add/ with new_holding=true is
    the one write path that creates the second row; every other path
    (plain add, toggle, bulk save) keeps reopening the existing row, which
    is covered by the reopen tests above and in users/tests.py."""

    def setUp(self):
        from datetime import date
        self.date = date
        self.user = User.objects.create_user(username='reapplier', password='x')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Reappliable Card', slug='reappliable-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.client.force_login(self.user)

    def test_new_holding_creates_a_second_row_leaving_the_old_one_closed(self):
        closed = UserCard.objects.create(
            user=self.user, card=self.card,
            opened_date=self.date(2021, 1, 1), closed_date=self.date(2022, 1, 1))

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id, 'new_holding': True, 'opened_date': '2026-08-01'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['created'])

        rows = UserCard.objects.filter(user=self.user, card=self.card).order_by('opened_date')
        self.assertEqual(rows.count(), 2)
        self.assertEqual(rows[0].id, closed.id)
        self.assertEqual(rows[0].closed_date, self.date(2022, 1, 1))
        self.assertIsNone(rows[1].closed_date)
        self.assertEqual(rows[1].opened_date, self.date(2026, 8, 1))

    def test_new_holding_rejected_when_an_open_row_already_exists(self):
        UserCard.objects.create(user=self.user, card=self.card, opened_date=self.date(2024, 1, 1))

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id, 'new_holding': True, 'opened_date': '2026-08-01'},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserCard.objects.filter(user=self.user, card=self.card).count(), 1)

    def test_plain_add_without_new_holding_still_reopens_the_closed_row(self):
        """Regression: the default behavior stays reopen-not-duplicate,
        same as story 07 — new_holding is opt-in."""
        closed = UserCard.objects.create(
            user=self.user, card=self.card,
            opened_date=self.date(2021, 1, 1), closed_date=self.date(2022, 1, 1))

        response = self.client.post(
            '/api/cards/user-cards/add/',
            {'card_id': self.card.id},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['created'])

        self.assertEqual(UserCard.objects.filter(user=self.user, card=self.card).count(), 1)
        closed.refresh_from_db()
        self.assertIsNone(closed.closed_date)

    def test_partial_constraint_still_rejects_two_open_rows(self):
        # A non-NULL owner is required to exercise this: NULL is distinct
        # from NULL under SQL, so two owner=NULL rows never collide even
        # under the partial index — the pre-existing leak documented in
        # story 13 and guarded against separately by
        # _get_or_create_owned_card.
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.user)
        primary = profile.primary_entity()
        UserCard.objects.create(
            user=self.user, card=self.card, owner=primary, opened_date=self.date(2024, 1, 1))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserCard.objects.create(
                    user=self.user, card=self.card, owner=primary, opened_date=self.date(2026, 1, 1))

    def test_two_closed_rows_for_the_same_product_are_allowed(self):
        UserCard.objects.create(
            user=self.user, card=self.card,
            opened_date=self.date(2021, 1, 1), closed_date=self.date(2022, 1, 1))
        UserCard.objects.create(
            user=self.user, card=self.card,
            opened_date=self.date(2023, 1, 1), closed_date=self.date(2024, 1, 1))
        self.assertEqual(UserCard.objects.filter(user=self.user, card=self.card).count(), 2)


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


from datetime import date
from decimal import Decimal
from .models import CardCredit, UserCreditUsage

class CreditUsageTests(TestCase):
    def setUp(self):
        self.category = SpendingCategory.objects.create(name='Travel', slug='travel')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Test Card', slug='test-card', issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)
            
        self.credit_monthly = CardCredit.objects.create(
            card=self.card, description='Monthly Credit', value=10.0, times_per_year=12
        )
        self.credit_quarterly = CardCredit.objects.create(
            card=self.card, description='Quarterly Credit', value=20.0, times_per_year=4
        )
        self.credit_annual = CardCredit.objects.create(
            card=self.card, description='Annual Credit', value=100.0, times_per_year=1
        )
        self.credit_semiannual = CardCredit.objects.create(
            card=self.card, description='Semi-Annual Credit', value=50.0, times_per_year=2
        )

    def test_get_period_key(self):
        test_date = date(2026, 7, 18)
        self.assertEqual(self.credit_monthly.get_period_key(test_date), '2026-07')
        self.assertEqual(self.credit_quarterly.get_period_key(test_date), '2026-Q3')
        self.assertEqual(self.credit_semiannual.get_period_key(test_date), '2026-H2')
        self.assertEqual(self.credit_annual.get_period_key(test_date), '2026')

        test_date_early = date(2026, 2, 5)
        self.assertEqual(self.credit_monthly.get_period_key(test_date_early), '2026-02')
        self.assertEqual(self.credit_quarterly.get_period_key(test_date_early), '2026-Q1')
        self.assertEqual(self.credit_semiannual.get_period_key(test_date_early), '2026-H1')
        self.assertEqual(self.credit_annual.get_period_key(test_date_early), '2026')

    def test_get_with_no_profile_returns_empty(self):
        response = self.client.get('/api/cards/credit-usage/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'usages': {}})

    def test_put_then_get_auth_round_trip(self):
        user = User.objects.create_user(username='u', password='x')
        self.client.force_login(user)

        response = self.client.put(
            '/api/cards/credit-usage/',
            {'usages': {str(self.credit_monthly.id): True, str(self.credit_quarterly.id): False}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['usages'], {
            str(self.credit_monthly.id): True,
            str(self.credit_quarterly.id): False,
        })

        profile = UserSpendingProfile.objects.get(user=user)
        current_month_key = self.credit_monthly.get_period_key(date.today())
        current_quarter_key = self.credit_quarterly.get_period_key(date.today())
        
        usage_monthly = UserCreditUsage.objects.get(
            profile=profile, card_credit=self.credit_monthly, period_key=current_month_key)
        self.assertTrue(usage_monthly.used)

        usage_quarterly = UserCreditUsage.objects.get(
            profile=profile, card_credit=self.credit_quarterly, period_key=current_quarter_key)
        self.assertFalse(usage_quarterly.used)

        get_response = self.client.get('/api/cards/credit-usage/')
        self.assertEqual(get_response.json()['usages'], {
            str(self.credit_monthly.id): True,
            str(self.credit_quarterly.id): False,
        })

    def test_put_creates_session_for_anon_user(self):
        response = self.client.put(
            '/api/cards/credit-usage/',
            {'usages': {str(self.credit_monthly.id): True}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.session.session_key)

        profile = UserSpendingProfile.objects.get(session_key=self.client.session.session_key)
        current_month_key = self.credit_monthly.get_period_key(date.today())
        self.assertTrue(UserCreditUsage.objects.filter(
            profile=profile, card_credit=self.credit_monthly, period_key=current_month_key, used=True
        ).exists())

        get_response = self.client.get('/api/cards/credit-usage/')
        self.assertEqual(get_response.json(), {'usages': {str(self.credit_monthly.id): True}})

    def test_get_filters_out_old_periods(self):
        user = User.objects.create_user(username='u', password='x')
        self.client.force_login(user)
        profile = UserSpendingProfile.objects.create(user=user)

        # Create usage for previous month
        UserCreditUsage.objects.create(
            profile=profile, card_credit=self.credit_monthly, period_key='2025-01', used=True
        )
        
        # Create usage for current month
        current_month_key = self.credit_monthly.get_period_key(date.today())
        UserCreditUsage.objects.create(
            profile=profile, card_credit=self.credit_monthly, period_key=current_month_key, used=True
        )

        # GET should only return the usage for the CURRENT period
        response = self.client.get('/api/cards/credit-usage/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['usages'], {
            str(self.credit_monthly.id): True
        })

    def test_put_object_form_stores_partial_amount(self):
        user = User.objects.create_user(username='u', password='x')
        self.client.force_login(user)

        response = self.client.put(
            '/api/cards/credit-usage/',
            {'usages': {str(self.credit_quarterly.id): {'used': True, 'amount': 12.5}}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['usages'], {str(self.credit_quarterly.id): True})

        usage = UserCreditUsage.objects.get(card_credit=self.credit_quarterly)
        self.assertEqual(usage.amount_used, Decimal('12.50'))

    def test_put_bool_form_keeps_an_existing_amount(self):
        # The modal still sends the bool form; ticking the box must not wipe
        # a partial amount that came in through import_credit_usage.
        user = User.objects.create_user(username='u', password='x')
        self.client.force_login(user)
        profile = UserSpendingProfile.objects.create(user=user)
        UserCreditUsage.objects.create(
            profile=profile, card_credit=self.credit_quarterly,
            period_key=self.credit_quarterly.get_period_key(date.today()),
            used=True, amount_used=Decimal('12.50'))

        self.client.put(
            '/api/cards/credit-usage/',
            {'usages': {str(self.credit_quarterly.id): True}},
            content_type='application/json')

        usage = UserCreditUsage.objects.get(card_credit=self.credit_quarterly)
        self.assertEqual(usage.amount_used, Decimal('12.50'))

    def test_put_rejects_a_non_numeric_amount(self):
        response = self.client.put(
            '/api/cards/credit-usage/',
            {'usages': {str(self.credit_quarterly.id): {'used': True, 'amount': 'lots'}}},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserCreditUsage.objects.exists())


class ImportCreditUsageCommandTests(TestCase):
    def setUp(self):
        import tempfile
        from .models import ProfileEntity
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.card = CreditCard.objects.create(
            name='Test Card', slug='test-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.dining = CardCredit.objects.create(
            card=self.card, description='Resy Credit', value=100, times_per_year=4)
        self.monthly = CardCredit.objects.create(
            card=self.card, description='Digital Entertainment Credit', value=25, times_per_year=12)
        self.user = User.objects.create_user(username='u', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.owner = ProfileEntity.objects.create(profile=self.profile, name='Alex', is_primary=True)
        self.holding = UserCard.objects.create(user=self.user, card=self.card, owner=self.owner)
        self.tmpdir = tempfile.mkdtemp()

    def _run(self, rows):
        import io, json, os
        from django.core.management import call_command
        path = os.path.join(self.tmpdir, 'usage.json')
        with open(path, 'w') as f:
            json.dump(rows, f)
        out = io.StringIO()
        call_command('import_credit_usage', file=path, username='u', stdout=out)
        return out.getvalue()

    def _row(self, **kw):
        row = {'card': 'test-card', 'owner': 'Alex', 'credit': 'resy',
               'period': '2026-Q4', 'amount': 61.73}
        row.update(kw)
        return row

    def test_partial_amount_lands_on_the_period(self):
        self._run([self._row()])
        usage = UserCreditUsage.objects.get(card_credit=self.dining, period_key='2026-Q4')
        self.assertTrue(usage.used)
        self.assertEqual(usage.amount_used, Decimal('61.73'))

    def test_rows_sharing_a_period_are_summed_and_a_rerun_is_idempotent(self):
        rows = [self._row(credit='digital', period='2026-05', amount=19.99),
                self._row(credit='digital', period='2026-05', amount=5.01)]
        self._run(rows)
        self._run(rows)
        usage = UserCreditUsage.objects.get(card_credit=self.monthly, period_key='2026-05')
        self.assertEqual(usage.amount_used, Decimal('25.00'))
        self.assertEqual(UserCreditUsage.objects.count(), 1)

    def test_unresolved_rows_are_named_not_dropped(self):
        out = self._run([
            self._row(credit='lululemon'),
            self._row(owner='Nobody'),
            self._row(period='2026-H2'),
            self._row(credit='credit'),  # matches both descriptions
            self._row(),
        ])
        self.assertIn('1 rows imported', out)
        self.assertIn("no credit 'lululemon' on test-card", out)
        self.assertIn("no open test-card owned by 'Nobody'", out)
        self.assertIn("period '2026-H2' is not in this credit's scheme", out)
        self.assertIn("matches 2 credit descriptions", out)

    def test_a_closed_holding_does_not_resolve(self):
        self.holding.closed_date = date(2026, 1, 1)
        self.holding.save()
        out = self._run([self._row()])
        self.assertIn("no open test-card owned by 'Alex'", out)
        self.assertFalse(UserCreditUsage.objects.exists())


class ImportCardsKeepsCreditUsageTests(TestCase):
    """Re-importing a card file must not cascade-delete recorded credit usage."""

    def setUp(self):
        import tempfile
        Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        RewardType.objects.create(name='Cashback', slug='cashback')
        SpendingCredit.objects.create(
            name='clear', display_name='Clear Plus', slug='clear',
            category=SpendingCategory.objects.create(name='Airlines', slug='airlines'))
        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user(username='u', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)

    def _import(self, credits):
        import io, json, os
        from django.core.management import call_command
        path = os.path.join(self.tmpdir, 'generic.json')
        with open(path, 'w') as f:
            json.dump([{'name': 'Test Card', 'issuer': 'Generic Bank', 'annual_fee': 95,
                        'reward_type': 'Cashback', 'verified': True,
                        'credits': credits}], f)
        call_command('import_cards', path, stdout=io.StringIO())
        return CreditCard.objects.get(name='Test Card')

    def test_value_and_description_changes_keep_usage(self):
        card = self._import([
            {'credit_type': 'clear', 'value': 100},
            {'description': 'Resy Credit', 'value': 100, 'times_per_year': 4},
            {'description': 'Retired Credit', 'value': 50},
        ])
        clear = card.credits.get(spending_credit__name='clear')
        resy = card.credits.get(description='Resy Credit')
        for credit in (clear, resy):
            UserCreditUsage.objects.create(
                profile=self.profile, card_credit=credit, period_key='2026', used=True)

        card = self._import([
            {'credit_type': 'clear', 'value': 219, 'description': 'CLEAR Plus'},
            {'description': 'Resy Credit', 'value': 100, 'times_per_year': 4,
             'offer_type': 'statement_credit'},
            {'description': 'Equinox Credit', 'value': 300},
        ])

        self.assertEqual(UserCreditUsage.objects.count(), 2)
        clear.refresh_from_db()
        self.assertEqual(clear.value, Decimal('219.00'))
        self.assertEqual(clear.description, 'CLEAR Plus')
        self.assertEqual(
            sorted(card.credits.values_list('description', flat=True)),
            ['CLEAR Plus', 'Equinox Credit', 'Resy Credit'])


class TemplatePagesTests(TestCase):
    def setUp(self):
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        app = SocialApp.objects.create(
            provider='google', name='Google', client_id='test', secret='test'
        )
        app.sites.add(Site.objects.get_current())

    def test_help_page_renders_successfully(self):
        response = self.client.get('/help/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'help.html')

    def test_resources_page_renders_successfully(self):
        response = self.client.get('/resources/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'resources.html')

    def test_landing_page_without_roadmap_renders_standard_hero(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertContains(response, 'Your cards, optimized.')
        self.assertNotContains(response, 'Welcome back.')

    def test_landing_page_with_roadmap_renders_welcome_back_hero(self):
        user = User.objects.create_user(username='testuser', password='password')
        profile = UserSpendingProfile.objects.create(user=user)
        
        from roadmaps.models import Roadmap, RoadmapCalculation
        roadmap = Roadmap.objects.create(profile=profile, name="Current Roadmap")
        RoadmapCalculation.objects.create(roadmap=roadmap, total_estimated_rewards=100.0, calculation_data={})
        
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertContains(response, 'Welcome back.')
        self.assertNotContains(response, 'Your cards, optimized.')


class CreditCurrencyValuationTests(TestCase):
    """CardCredit.currency must discount points-denominated credits to real
    dollars instead of being counted at face value (Obsidian side-projects/mycreditcard.guru/progress.md's
    former 'Open' item / Obsidian side-projects/mycreditcard.guru/Requirements/Complete/PLAN_POINTS_CURRENCY_CREDIT_VALUATION_complete.md)."""

    def setUp(self):
        from .models import PointsProgram, PointsValuation
        self.PointsProgram = PointsProgram
        self.PointsValuation = PointsValuation
        self.program = PointsProgram.objects.create(
            name='Southwest Rapid Rewards', slug='southwest_rapid_rewards',
            currency_code='SOUTHWEST')
        PointsValuation.objects.create(
            points_program=self.program, user=None, value=0.0140)

    def test_usd_and_blank_currency_rate_to_one(self):
        from .valuations import credit_currency_rate
        self.assertEqual(credit_currency_rate('USD'), 1.0)
        self.assertEqual(credit_currency_rate(''), 1.0)
        self.assertEqual(credit_currency_rate(None), 1.0)

    def test_seeded_currency_resolves_to_its_default_valuation(self):
        from .valuations import credit_currency_rate
        self.assertEqual(credit_currency_rate('SOUTHWEST'), 0.0140)

    def test_user_override_wins_over_system_default(self):
        from .valuations import credit_currency_rate
        user = User.objects.create_user(username='pointer', email='p@example.com')
        self.PointsValuation.objects.create(
            points_program=self.program, user=user, value=0.0200)
        self.assertEqual(credit_currency_rate('SOUTHWEST', user), 0.0200)
        # A different (anonymous) user still gets the system default.
        self.assertEqual(credit_currency_rate('SOUTHWEST'), 0.0140)

    def test_unmapped_non_usd_currency_falls_back_to_safety_net(self):
        from .valuations import credit_currency_rate, UNMAPPED_CURRENCY_RATE
        with self.assertLogs('cards.valuations', level='WARNING'):
            rate = credit_currency_rate('ALASKA')
        self.assertEqual(rate, UNMAPPED_CURRENCY_RATE)

    def test_card_credit_annual_value_discounts_points_currency(self):
        from .models import CardCredit, CreditCard, Issuer, RewardType
        cashback = RewardType.objects.create(name='Cashback2', slug='cashback2')
        issuer = Issuer.objects.create(name='Test Bank', slug='test-bank')
        card = CreditCard.objects.create(
            name='Southwest Test Card', slug='southwest-test-card', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        credit = CardCredit.objects.create(
            card=card, description='Anniversary Points', value=7500,
            times_per_year=1, currency='SOUTHWEST')
        # 7,500 pts x $0.014/pt = $105, not $7,500 face value.
        self.assertEqual(credit.annual_value, 105.0)

        usd_credit = CardCredit.objects.create(
            card=card, description='Statement Credit', value=300, times_per_year=1)
        self.assertEqual(usd_credit.annual_value, 300.0)


class CreditMathBuilderAPITests(TestCase):
    """Phase Q (Obsidian side-projects/mycreditcard.guru/stories/02-builder-credit-math.md): the spending
    builder needs `annual_value` on card credits and a `typical_value` on
    the spending-credit catalog so it can show real dollar figures next to
    the "Credits You Use" checkboxes instead of none at all."""

    def setUp(self):
        from .models import CardCredit, PointsProgram, PointsValuation
        self.category = SpendingCategory.objects.create(name='Travel2', slug='travel2')
        self.lounge = SpendingCredit.objects.create(
            name='Lounge2', slug='lounge2', display_name='Lounge Access 2',
            category=self.category)
        self.no_card_credit = SpendingCredit.objects.create(
            name='Unclaimed', slug='unclaimed', display_name='Unclaimed Credit',
            category=self.category)

        cashback = RewardType.objects.create(name='CashbackQ', slug='cashback-q')
        issuer = Issuer.objects.create(name='Test Bank Q', slug='test-bank-q')

        program = PointsProgram.objects.create(
            name='Test Points Program', slug='test-points-program-q',
            currency_code='TESTPTSQ')
        PointsValuation.objects.create(points_program=program, user=None, value=0.01)

        self.card_a = CreditCard.objects.create(
            name='Card A', slug='card-a-q', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)
        self.card_b = CreditCard.objects.create(
            name='Card B', slug='card-b-q', issuer=issuer,
            signup_bonus_type=cashback, primary_reward_type=cashback)

        # Points-denominated credit: 10,000 pts x $0.01 = $100, not $10,000.
        self.points_credit = CardCredit.objects.create(
            card=self.card_a, spending_credit=self.lounge,
            description='Lounge points credit', value=10000, times_per_year=1,
            currency='TESTPTSQ')
        # A second, cheaper carrying card so the median (typical_value) of
        # [100, 50] is 75 — distinct from either individual card's value,
        # proving it's really a median and not just "the first card found".
        CardCredit.objects.create(
            card=self.card_b, spending_credit=self.lounge,
            description='Lounge USD credit', value=50, times_per_year=1)

    def test_card_credit_serializer_exposes_discounted_annual_value(self):
        response = self.client.get(f'/api/cards/cards/{self.card_a.id}/')
        self.assertEqual(response.status_code, 200)
        credits = response.json()['credits']
        credit_data = next(c for c in credits if c['id'] == self.points_credit.id)
        self.assertIn('annual_value', credit_data)
        self.assertEqual(credit_data['annual_value'], 100.0)

    def test_spending_credits_endpoint_returns_typical_value(self):
        response = self.client.get('/api/cards/spending-credits/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload.get('results', payload) if isinstance(payload, dict) else payload

        lounge_data = next(c for c in results if c['slug'] == 'lounge2')
        self.assertEqual(lounge_data['typical_value'], 75.0)

        unclaimed_data = next(c for c in results if c['slug'] == 'unclaimed')
        self.assertIsNone(unclaimed_data['typical_value'])


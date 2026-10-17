"""Tests for the card scorecard: fee vs. statement credits used, per card."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    CardCredit, CreditCard, Issuer, ProfileEntity, RewardType, UserCard,
    UserCreditUsage, UserSpendingProfile,
)
from .scorecard import build_scorecard, next_fee_date, period_bounds

TODAY = date(2026, 10, 11)


class ScorecardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='jamie', password='x')
        cls.profile = UserSpendingProfile.objects.create(user=cls.user)
        cls.owner = ProfileEntity.objects.create(
            profile=cls.profile, name='Jamie', is_primary=True)
        issuer = Issuer.objects.create(name='Amex', slug='amex')
        cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        cls.card = CreditCard.objects.create(
            name='Platinum', slug='platinum', issuer=issuer, annual_fee=Decimal('895'),
            signup_bonus_type=cashback, primary_reward_type=cashback)
        cls.resy = CardCredit.objects.create(
            card=cls.card, description='Resy Credit', value=100, times_per_year=4)
        cls.clear = CardCredit.objects.create(
            card=cls.card, description='CLEAR Credit', value=219, times_per_year=1,
            offer_type='statement_credit')
        cls.lounge = CardCredit.objects.create(
            card=cls.card, description='Lounge Access', value=850, offer_type='membership')
        cls.holding = UserCard.objects.create(
            user=cls.user, card=cls.card, owner=cls.owner, opened_date=date(2023, 12, 15))

    def use(self, credit, period, amount=None):
        UserCreditUsage.objects.create(
            profile=self.profile, card_credit=credit, period_key=period,
            used=True, amount_used=amount)

    def row(self):
        rows, totals = build_scorecard(self.user, TODAY)
        self.assertEqual(len(rows), 1)
        return rows[0]


class PeriodMathTests(TestCase):
    def test_period_bounds_cover_each_scheme(self):
        self.assertEqual(period_bounds('2026-02'), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(period_bounds('2026-12'), (date(2026, 12, 1), date(2026, 12, 31)))
        self.assertEqual(period_bounds('2026-Q4'), (date(2026, 10, 1), date(2026, 12, 31)))
        self.assertEqual(period_bounds('2026-H1'), (date(2026, 1, 1), date(2026, 6, 30)))
        self.assertEqual(period_bounds('2025'), (date(2025, 1, 1), date(2025, 12, 31)))

    def test_next_fee_is_the_next_anniversary(self):
        self.assertEqual(next_fee_date(date(2023, 12, 15), TODAY), date(2026, 12, 15))
        self.assertEqual(next_fee_date(date(2016, 8, 29), TODAY), date(2027, 8, 29))
        self.assertEqual(next_fee_date(date(2020, 10, 11), TODAY), TODAY)
        self.assertEqual(next_fee_date(date(2024, 2, 29), TODAY), date(2027, 2, 28))
        self.assertIsNone(next_fee_date(None, TODAY))


class BuildScorecardTests(ScorecardTestCase):
    def test_fee_and_available_count_statement_credits_only(self):
        row = self.row()
        self.assertEqual(row['fee'], 895)
        self.assertEqual(row['available'], 400 + 219)  # lounge is a membership
        self.assertEqual(row['next_fee'], date(2026, 12, 15))

    def test_partial_amount_counts_as_entered(self):
        self.use(self.resy, '2026-Q4', Decimal('61.73'))
        self.assertAlmostEqual(self.row()['used'], 61.73)

    def test_null_amount_counts_the_full_period_value(self):
        self.use(self.resy, '2026-Q2')
        self.assertEqual(self.row()['used'], 100)

    def test_periods_overlapping_the_window_count_including_the_current_one(self):
        self.use(self.resy, '2025-Q3')               # ended 9/30/25: outside
        self.use(self.resy, '2025-Q4')               # overlaps 10/12/25 onward
        self.use(self.resy, '2026-Q4', Decimal('10'))  # in progress
        self.use(self.clear, '2026')                  # annual, in progress
        self.use(self.clear, '2027')                  # hasn't started
        self.assertEqual(self.row()['used'], 100 + 10 + 219)

    def test_non_statement_credit_usage_is_excluded(self):
        self.use(self.lounge, '2026')
        self.assertEqual(self.row()['used'], 0)

    def test_net_verdict_and_gap_closers(self):
        self.use(self.clear, '2026')
        self.use(self.resy, '2026-Q4', Decimal('61.73'))
        row = self.row()
        self.assertAlmostEqual(row['net'], 219 + 61.73 - 895)
        self.assertEqual(row['verdict'], 'short')
        self.assertEqual([u['name'] for u in row['unused']], ['Resy Credit'])
        self.assertAlmostEqual(row['unused'][0]['left'], 38.27)
        self.assertEqual(row['gap_closers'], row['unused'])
        self.assertFalse(row['gap_closed'])

    def test_an_expired_credit_still_counts_usage_but_not_available(self):
        self.clear.end_date = date(2026, 6, 30)
        self.clear.save()
        self.use(self.clear, '2026')
        row = self.row()
        self.assertEqual(row['available'], 400)
        self.assertEqual(row['used'], 219)
        self.assertNotIn('CLEAR Credit', [u['name'] for u in row['unused']])

    def test_a_credit_that_has_not_started_is_left_out(self):
        CardCredit.objects.create(
            card=self.card, description='The Edit', value=250, times_per_year=4,
            start_date=date(2027, 1, 1))
        row = self.row()
        self.assertEqual(row['available'], 400 + 219)
        self.assertNotIn('The Edit', [u['name'] for u in row['unused']])

    def test_closed_card_is_excluded(self):
        self.holding.closed_date = date(2026, 1, 1)
        self.holding.save()
        rows, totals = build_scorecard(self.user, TODAY)
        self.assertEqual(rows, [])
        self.assertEqual(totals, {'fees': 0, 'used': 0, 'net': 0})

    def test_a_card_held_twice_shows_its_usage_once(self):
        lisa = ProfileEntity.objects.create(profile=self.profile, name='Lisa')
        UserCard.objects.create(user=self.user, card=self.card, owner=lisa)
        self.use(self.clear, '2026')
        rows, totals = build_scorecard(self.user, TODAY)
        self.assertEqual([r['used'] for r in rows], [219, 0])
        self.assertEqual(rows[1]['usage_shown_on'], self.holding)
        self.assertEqual(totals['used'], 219)


class ScorecardViewTests(ScorecardTestCase):
    def test_renders_the_users_cards(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('scorecard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Platinum')
        self.assertContains(response, '$895')

    def test_redirects_to_login_when_anonymous(self):
        response = self.client.get(reverse('scorecard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response['Location'])

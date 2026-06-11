"""Tests for the phone wallet view and date-aware reward categories."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    CreditCard, Issuer, RewardCategory, RewardType, SpendingCategory,
    UserCard,
)
from .wallet import build_wallet_rows, quarter_end


class WalletTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='jamie', password='x')
        cls.issuer = Issuer.objects.create(name='Chase', slug='chase')
        cls.cashback = RewardType.objects.create(name='Cashback', slug='cashback')

        cls.dining = SpendingCategory.objects.create(
            name='dining', slug='dining', display_name='Dining')
        cls.gas = SpendingCategory.objects.create(
            name='gas', slug='gas', display_name='Gas')
        cls.amazon = SpendingCategory.objects.create(
            name='amazon', slug='amazon', display_name='Amazon')
        cls.other = SpendingCategory.objects.create(
            name='other', slug='other', display_name='Other')

        def card(name, slug):
            return CreditCard.objects.create(
                name=name, slug=slug, issuer=cls.issuer,
                signup_bonus_type=cls.cashback, primary_reward_type=cls.cashback,
            )

        cls.flex = card('Freedom Flex', 'freedom-flex')
        cls.flat = card('Flat Two', 'flat-two')

        def reward(card_obj, category, rate, start=None, end=None, cap=None):
            return RewardCategory.objects.create(
                card=card_obj, category=category,
                reward_rate=Decimal(str(rate)), reward_type=cls.cashback,
                start_date=start, end_date=end, max_annual_spend=cap,
            )

        # Flex: permanent 3% dining, 1% base, rotating 5% amazon in Q2 2026
        # and an EXPIRED rotating 5% gas from Q1 2025.
        reward(cls.flex, cls.dining, 3)
        reward(cls.flex, cls.other, 1)
        reward(cls.flex, cls.amazon, 5,
               start=date(2026, 4, 1), end=date(2026, 6, 30), cap=Decimal('1500'))
        reward(cls.flex, cls.gas, 5,
               start=date(2025, 1, 1), end=date(2025, 3, 31), cap=Decimal('1500'))

        # Flat card: 2% on everything, plus a 2% dining entry that should be
        # folded into base (doesn't beat its own base rate).
        reward(cls.flat, cls.other, 2)
        reward(cls.flat, cls.dining, 2)

        UserCard.objects.create(user=cls.user, card=cls.flex,
                                opened_date=date(2024, 1, 15))
        UserCard.objects.create(user=cls.user, card=cls.flat,
                                opened_date=date(2024, 6, 1))

    def rows_by_slug(self, today):
        rows, base = build_wallet_rows(self.user, today)
        return {r['category'].slug: r for r in rows}, base

    def test_current_quarter_rotating_category_shown(self):
        rows, _ = self.rows_by_slug(date(2026, 6, 11))
        self.assertIn('amazon', rows)
        self.assertEqual(rows['amazon']['card'], self.flex)
        self.assertEqual(rows['amazon']['rate'], Decimal('5'))
        self.assertTrue(rows['amazon']['is_rotating'])
        self.assertEqual(rows['amazon']['end_date'], date(2026, 6, 30))

    def test_expired_rotating_category_not_shown(self):
        rows, _ = self.rows_by_slug(date(2026, 6, 11))
        # The Q1-2025 5% gas expired; gas must not appear as a bonus category.
        self.assertNotIn('gas', rows)

    def test_rotating_category_shown_only_inside_window(self):
        rows_q1, _ = self.rows_by_slug(date(2026, 2, 1))
        self.assertNotIn('amazon', rows_q1)

    def test_base_card_is_best_flat_rate(self):
        _, base = self.rows_by_slug(date(2026, 6, 11))
        self.assertEqual(base['card'], self.flat)
        self.assertEqual(base['rate'], Decimal('2'))

    def test_category_not_beating_base_is_folded_into_base(self):
        rows, _ = self.rows_by_slug(date(2026, 6, 11))
        # Flex dining 3% beats base 2%, so dining stays...
        self.assertIn('dining', rows)
        self.assertEqual(rows['dining']['card'], self.flex)
        # ...but the flat card's 2% dining row would not have survived alone.
        self.assertEqual(rows['dining']['rate'], Decimal('3'))

    def test_closed_cards_excluded(self):
        UserCard.objects.filter(card=self.flex).update(closed_date=date(2026, 1, 1))
        rows, base = self.rows_by_slug(date(2026, 6, 11))
        self.assertNotIn('amazon', rows)
        self.assertEqual(base['card'], self.flat)

    def test_view_requires_login(self):
        response = self.client.get(reverse('wallet'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_view_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('wallet'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Freedom Flex')
        self.assertContains(response, 'All other purchases')


class QuarterEndTest(TestCase):
    def test_quarter_ends(self):
        self.assertEqual(quarter_end(date(2026, 1, 15)), date(2026, 3, 31))
        self.assertEqual(quarter_end(date(2026, 6, 11)), date(2026, 6, 30))
        self.assertEqual(quarter_end(date(2026, 9, 30)), date(2026, 9, 30))
        self.assertEqual(quarter_end(date(2026, 11, 2)), date(2026, 12, 31))

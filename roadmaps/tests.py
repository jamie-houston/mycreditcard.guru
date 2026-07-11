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


class EligibilityRuleTests(TestCase):
    """S3: data-driven issuer application + bonus rules (roadmaps/eligibility.py).

    Rules are evaluated against plain history objects (card / opened_date /
    closed_date / bonus_earned_date), so these tests use lightweight
    namespaces instead of UserCard rows."""

    def setUp(self):
        from datetime import date
        self.today = date(2026, 7, 1)
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.chase = Issuer.objects.create(name='Chase', slug='chase')
        self.amex = Issuer.objects.create(name='American Express', slug='american-express')
        self.citi = Issuer.objects.create(name='Citi', slug='citi')
        self.bofa = Issuer.objects.create(name='Bank of America', slug='bank-of-america')
        self.capone = Issuer.objects.create(name='Capital One', slug='capital-one')
        self.generic = Issuer.objects.create(name='Generic Bank', slug='generic-bank')

    def _card(self, name, issuer, card_type='personal', metadata=None):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=issuer, card_type=card_type,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            metadata=metadata or {})

    def _held(self, card, opened_days_ago=None, closed_days_ago=None,
              bonus_earned_days_ago=None):
        from datetime import timedelta
        from types import SimpleNamespace
        days = lambda n: self.today - timedelta(days=n) if n is not None else None
        return SimpleNamespace(
            card=card,
            opened_date=days(opened_days_ago),
            closed_date=days(closed_days_ago),
            bonus_earned_date=days(bonus_earned_days_ago),
        )

    def test_months_before_is_calendar_accurate(self):
        from datetime import date
        from .eligibility import months_before
        self.assertEqual(months_before(date(2026, 7, 1), 24), date(2024, 7, 1))
        # Clamps to month end instead of drifting like 24*30 days did
        self.assertEqual(months_before(date(2026, 3, 31), 1), date(2026, 2, 28))
        self.assertEqual(months_before(date(2026, 1, 15), 6), date(2025, 7, 15))

    def test_chase_524_counts_personal_cards_from_any_issuer(self):
        from .eligibility import application_block
        candidate = self._card('Chase Candidate', self.chase)
        others = [self._card(f'Card {i}', self.generic) for i in range(5)]
        history = [self._held(c, opened_days_ago=100 + i * 60)
                   for i, c in enumerate(others)]
        self.assertIsNotNone(application_block(candidate, history, self.today))
        # At 4/24 the application goes through
        self.assertIsNone(application_block(candidate, history[:4], self.today))
        # Cards opened outside the 24-month window don't count
        old = [self._held(c, opened_days_ago=800 + i) for i, c in enumerate(others)]
        self.assertIsNone(application_block(candidate, old, self.today))

    def test_chase_524_business_cards_dont_count_unless_they_report(self):
        from .eligibility import application_block
        candidate = self._card('Chase Candidate', self.chase)
        personal = [self._card(f'P{i}', self.generic) for i in range(4)]
        history = [self._held(c, opened_days_ago=100) for c in personal]
        # A generic business card doesn't report to personal credit: still 4/24
        biz = self._card('Generic Biz', self.generic, card_type='business')
        self.assertIsNone(application_block(
            candidate, history + [self._held(biz, opened_days_ago=50)], self.today))
        # A Capital One business card DOES report: that makes 5/24
        c1_biz = self._card('C1 Biz', self.capone, card_type='business')
        self.assertIsNotNone(application_block(
            candidate, history + [self._held(c1_biz, opened_days_ago=50)], self.today))

    def test_bofa_234_only_counts_bofa_cards(self):
        from .eligibility import application_block
        candidate = self._card('BofA Candidate', self.bofa)
        b1 = self._card('BofA One', self.bofa)
        b2 = self._card('BofA Two', self.bofa)
        recent = [self._held(b1, opened_days_ago=10),
                  self._held(b2, opened_days_ago=20)]
        # 2 BofA cards in 30 days -> blocked by 2/30
        self.assertIsNotNone(application_block(candidate, recent, self.today))
        # Two recent cards from another issuer are irrelevant
        g = [self._held(self._card(f'G{i}', self.generic), opened_days_ago=10)
             for i in range(2)]
        self.assertIsNone(application_block(candidate, g, self.today))

    def test_capital_one_one_per_six_months(self):
        from .eligibility import application_block
        candidate = self._card('C1 Candidate', self.capone)
        c1 = self._card('C1 Existing', self.capone)
        self.assertIsNotNone(application_block(
            candidate, [self._held(c1, opened_days_ago=90)], self.today))
        self.assertIsNone(application_block(
            candidate, [self._held(c1, opened_days_ago=220)], self.today))

    def test_amex_lifetime_is_per_card_and_survives_closure(self):
        from .eligibility import bonus_ineligibility
        gold = self._card('Amex Gold', self.amex)
        plat = self._card('Amex Platinum', self.amex)
        held_gold = self._held(gold, opened_days_ago=1200, closed_days_ago=800)
        self.assertIsNotNone(bonus_ineligibility(gold, [held_gold], self.today))
        # Per-card, not per-issuer: Platinum bonus is still earnable
        self.assertIsNone(bonus_ineligibility(plat, [held_gold], self.today))

    def test_citi_48_month_window(self):
        from .eligibility import bonus_ineligibility
        card = self._card('Citi Card', self.citi)
        recent = self._held(card, opened_days_ago=1500,
                            bonus_earned_days_ago=47 * 30)
        self.assertIsNotNone(bonus_ineligibility(card, [recent], self.today))
        old = self._held(card, opened_days_ago=2000,
                         bonus_earned_days_ago=50 * 31)
        self.assertIsNone(bonus_ineligibility(card, [old], self.today))

    def test_citi_bonus_date_approximated_from_opened_date(self):
        """No bonus_earned_date recorded: assume opened + ~3 months."""
        from .eligibility import bonus_ineligibility
        card = self._card('Citi Card', self.citi)
        # Opened 47 months ago -> approx bonus 44 months ago -> in window
        inside = self._held(card, opened_days_ago=47 * 30)
        self.assertIsNotNone(bonus_ineligibility(card, [inside], self.today))
        # Opened 55 months ago -> approx bonus 52 months ago -> out of window
        outside = self._held(card, opened_days_ago=55 * 31)
        self.assertIsNone(bonus_ineligibility(card, [outside], self.today))

    def test_sapphire_metadata_overrides_issuer_default(self):
        from .eligibility import bonus_ineligibility
        sapphire = self._card('Sapphire Test', self.chase, metadata={
            'bonus_eligibility': {'once_per_lifetime': True,
                                  'label': 'Sapphire once per lifetime'}})
        self.assertIsNone(bonus_ineligibility(sapphire, [], self.today))
        prior = self._held(sapphire, opened_days_ago=2000, closed_days_ago=1000)
        note = bonus_ineligibility(sapphire, [prior], self.today)
        self.assertIn('Sapphire once per lifetime', note)

    def test_southwest_family_rules(self):
        from .eligibility import application_block, bonus_ineligibility
        family_meta = {
            'application_family': 'southwest-personal',
            'bonus_eligibility': {'months_since_bonus': 24,
                                  'family': 'southwest-personal',
                                  'label': 'Southwest 24-month rule'}}
        plus = self._card('SW Plus', self.chase, metadata=family_meta)
        priority = self._card('SW Priority', self.chase, metadata=family_meta)
        # Holding one open SW personal card blocks applying for another
        holding = self._held(plus, opened_days_ago=400)
        self.assertIsNotNone(application_block(priority, [holding], self.today))
        # Closed card doesn't block the application...
        closed = self._held(plus, opened_days_ago=400, closed_days_ago=100)
        self.assertIsNone(application_block(priority, [closed], self.today))
        # ...but a family bonus earned within 24 months zeroes the bonus
        self.assertIsNotNone(bonus_ineligibility(priority, [closed], self.today))


class BonusVelocityTests(TestCase):
    """S3: signup bonuses limited by how fast the user can actually spend."""

    def setUp(self):
        from cards.models import SpendingCategory, SpendingAmount
        self.user = User.objects.create_user(username='velocity', email='v@example.com')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.points = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        other = SpendingCategory.objects.create(name='Other', slug='other')
        SpendingAmount.objects.create(profile=self.profile, category=other,
                                      monthly_amount=Decimal('2000'))

    def _card(self, name, requirement):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=self.issuer,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            signup_bonus_amount=500,
            metadata={'reward_value_multiplier': 0.01,
                      'signup_bonus': {'bonus_amount': 500,
                                       'spending_requirement': requirement,
                                       'time_limit_months': 6}})

    def test_bonus_months_needed(self):
        from .recommendation_engine import RecommendationEngine
        engine = RecommendationEngine(self.profile)
        # $10K requirement at $2K/mo = 5 months of total spending
        self.assertAlmostEqual(
            engine._bonus_months_needed(self._card('Ten K', 10000)), 5.0)
        # No requirement -> no months consumed
        self.assertEqual(
            engine._bonus_months_needed(self._card('Free Bonus', 0)), 0.0)

    def test_no_spending_means_infinite_months(self):
        from .recommendation_engine import RecommendationEngine
        empty_profile = UserSpendingProfile.objects.create(
            user=User.objects.create_user(username='broke', email='b@example.com'))
        engine = RecommendationEngine(empty_profile)
        self.assertEqual(
            engine._bonus_months_needed(self._card('Any', 5000)), float('inf'))


class CreditAllocationTests(TestCase):
    """A5: _allocate_portfolio_credits is the single dedup authority for
    stackability — non-stackable credits (membership/subscription benefits)
    count once per portfolio; stackable ones count per card."""

    def setUp(self):
        from cards.models import SpendingCategory, SpendingCredit, UserSpendingCreditPreference
        self.user = User.objects.create_user(username='allocator', email='a@example.com')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        travel = SpendingCategory.objects.create(name='Travel', slug='travel')
        dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        self.lounge = SpendingCredit.objects.create(
            name='Airport Lounge', slug='airport_lounge', display_name='Airport Lounge',
            category=travel, stackable=False)
        self.uber_eats = SpendingCredit.objects.create(
            name='Uber Eats', slug='uber_eats', display_name='Uber Eats',
            category=dining, stackable=True)
        UserSpendingCreditPreference.objects.create(
            profile=self.profile, spending_credit=self.lounge, values_credit=True)
        UserSpendingCreditPreference.objects.create(
            profile=self.profile, spending_credit=self.uber_eats, values_credit=True)

    def _card(self, name):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)

    def _credit(self, card, spending_credit, value):
        from cards.models import CardCredit
        return CardCredit.objects.create(
            card=card, spending_credit=spending_credit,
            description=spending_credit.display_name, value=Decimal(str(value)))

    def _engine(self):
        from .recommendation_engine import RecommendationEngine
        return RecommendationEngine(self.profile)

    def test_non_stackable_duplicate_counts_once_with_info_line_on_loser(self):
        low = self._card('Low Lounge Card')
        high = self._card('High Lounge Card')
        self._credit(low, self.lounge, 300)
        self._credit(high, self.lounge, 550)

        allocation = self._engine()._allocate_portfolio_credits([low, high])

        low_value, low_items = allocation[low.id]
        high_value, high_items = allocation[high.id]
        self.assertEqual(high_value, 550.0)
        self.assertEqual(low_value, 0.0)
        # Winner gets a real credit line item, not an info line
        self.assertTrue(any(i['type'] == 'credit' for i in high_items))
        # Loser gets a $0 info line naming the winning card
        info_items = [i for i in low_items if i['type'] == 'info']
        self.assertEqual(len(info_items), 1)
        self.assertEqual(info_items[0]['category_rewards'], 0)
        self.assertIn('High Lounge Card', info_items[0]['calculation'])

    def test_stackable_duplicate_counts_on_every_card(self):
        card_a = self._card('Uber Card A')
        card_b = self._card('Uber Card B')
        self._credit(card_a, self.uber_eats, 120)
        self._credit(card_b, self.uber_eats, 120)

        allocation = self._engine()._allocate_portfolio_credits([card_a, card_b])

        self.assertEqual(allocation[card_a.id][0], 120.0)
        self.assertEqual(allocation[card_b.id][0], 120.0)

    def test_opt_out_row_equals_absent_row(self):
        from cards.models import UserSpendingCreditPreference
        card = self._card('Lounge Card')
        self._credit(card, self.lounge, 300)

        # No preference row at all (setUp's blanket preference removed)
        UserSpendingCreditPreference.objects.filter(
            profile=self.profile, spending_credit=self.lounge).delete()
        no_row_value = self._engine()._allocate_portfolio_credits([card])[card.id][0]

        # Explicit opt-out row (values_credit=False)
        UserSpendingCreditPreference.objects.create(
            profile=self.profile, spending_credit=self.lounge, values_credit=False)
        opt_out_value = self._engine()._allocate_portfolio_credits([card])[card.id][0]

        self.assertEqual(no_row_value, 0.0)
        self.assertEqual(opt_out_value, 0.0)

    def test_tie_break_is_deterministic_on_card_id(self):
        first = self._card('First Lounge Card')
        second = self._card('Second Lounge Card')
        self.assertLess(first.id, second.id)
        self._credit(first, self.lounge, 400)
        self._credit(second, self.lounge, 400)

        allocation = self._engine()._allocate_portfolio_credits([first, second])

        # Equal value -> lowest card id wins
        self.assertEqual(allocation[first.id][0], 400.0)
        self.assertEqual(allocation[second.id][0], 0.0)
        # Order of the input list must not change the outcome
        reversed_allocation = self._engine()._allocate_portfolio_credits([second, first])
        self.assertEqual(reversed_allocation[first.id][0], 400.0)
        self.assertEqual(reversed_allocation[second.id][0], 0.0)

    def test_cancel_counterfactual_credits_already_covered_by_held_cards(self):
        """Evaluating whether to cancel a card must account for a non-stackable
        credit already carried by a higher-value held card — the cancel
        candidate shouldn't get credit for a benefit the user keeps regardless."""
        held_high = self._card('Held High Lounge Card')
        cancel_candidate = self._card('Cancel Candidate Lounge Card')
        self._credit(held_high, self.lounge, 550)
        self._credit(cancel_candidate, self.lounge, 300)

        allocation = self._engine()._allocate_portfolio_credits(
            [held_high, cancel_candidate])

        # The candidate contributes $0 credit value to the cancel decision —
        # the lounge benefit survives on the held card either way.
        self.assertEqual(allocation[cancel_candidate.id][0], 0.0)
        self.assertEqual(allocation[held_high.id][0], 550.0)


class QuickRecommendationSafetyTests(TestCase):
    """The quick-rec endpoint must never mutate stored profile data
    (the old behavior deleted and recreated it from the form payload)."""

    def setUp(self):
        from cards.models import SpendingCategory, SpendingAmount, UserCard
        self.user = User.objects.create_user(
            username='saved', email='saved@example.com', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        SpendingAmount.objects.create(
            profile=self.profile, category=self.dining,
            monthly_amount=Decimal('999'))
        self.card = CreditCard.objects.create(
            name='Stored Card', slug='stored-card', issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)
        from datetime import date
        UserCard.objects.create(user=self.user, card=self.card,
                                opened_date=date(2024, 1, 1))

    def test_quick_recommendation_leaves_stored_profile_alone(self):
        from cards.models import UserCard
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {'spending_amounts': {str(self.dining.id): '123.00'},
             'user_cards': [],
             'max_recommendations': 2},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        # Stored spending survives with its original amount
        amounts = list(self.profile.spending_amounts.all())
        self.assertEqual(len(amounts), 1)
        self.assertEqual(amounts[0].monthly_amount, Decimal('999'))
        # Stored card ownership survives (payload said "no cards")
        self.assertTrue(UserCard.objects.filter(
            user=self.user, card=self.card).exists())

    def test_max_recommendations_defaults_to_one(self):
        """Empty payload -> serializer default is 1 new card, not 5."""
        from .serializers import GenerateRoadmapSerializer
        serializer = GenerateRoadmapSerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['max_recommendations'], 1)


class RoadmapPersistenceTests(TestCase):
    """B1/B2/B3: generating a roadmap persists it as "Current Roadmap" (both
    auth and anon-via-session), survives reload via GET .../current/, and
    regenerating overwrites rather than duplicating."""

    def setUp(self):
        from cards.models import SpendingCategory
        self.user = User.objects.create_user(
            username='persist', email='persist@example.com', password='x')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        self.card = CreditCard.objects.create(
            name='Persist Card', slug='persist-card', issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)

    def _payload(self, amount='500.00'):
        return {
            'spending_amounts': {str(self.dining.id): amount},
            'user_cards': [],
            'max_recommendations': 1,
        }

    def test_generate_persists_current_roadmap_for_auth_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        profile = UserSpendingProfile.objects.get(user=self.user)
        roadmap = Roadmap.objects.get(profile=profile, name='Current Roadmap')
        self.assertTrue(hasattr(roadmap, 'calculation'))
        self.assertIn('response', roadmap.calculation.calculation_data)
        self.assertIn('generated_at', roadmap.calculation.calculation_data)

    def test_generate_persists_for_fresh_anon_client(self):
        """Regression test for the B1 session-rollback trap: a brand new
        anonymous client (no session cookie yet) must still get a durable
        session and a persisted Current Roadmap from a single request."""
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)
        profile = UserSpendingProfile.objects.get(session_key=session_key)
        self.assertTrue(
            Roadmap.objects.filter(profile=profile, name='Current Roadmap').exists()
        )

    def test_get_current_returns_stored_response(self):
        self.client.force_login(self.user)
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

        response = self.client.get('/api/roadmaps/current/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('recommendations', data)
        self.assertIn('generated_at', data)

    def test_get_current_404_when_nothing_generated(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/roadmaps/current/')
        self.assertEqual(response.status_code, 404)

    def test_regenerate_overwrites_rather_than_duplicates(self):
        self.client.force_login(self.user)
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload('500.00'),
            content_type='application/json')
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload('900.00'),
            content_type='application/json')

        profile = UserSpendingProfile.objects.get(user=self.user)
        self.assertEqual(
            Roadmap.objects.filter(profile=profile, name='Current Roadmap').count(), 1
        )
        response = self.client.get('/api/roadmaps/current/')
        stored_request = RoadmapCalculation.objects.get(
            roadmap__profile=profile, roadmap__name='Current Roadmap'
        ).calculation_data['request']
        self.assertEqual(stored_request['spending_amounts'][str(self.dining.id)], '900.00')

    def test_generate_leaves_real_profile_untouched_after_persistence(self):
        """The scratch-write rollback (pre-existing behavior) must still hold
        even though a real write (Current Roadmap) now happens afterward."""
        from cards.models import SpendingAmount
        self.client.force_login(self.user)
        profile = UserSpendingProfile.objects.create(user=self.user) if not \
            UserSpendingProfile.objects.filter(user=self.user).exists() else \
            UserSpendingProfile.objects.get(user=self.user)
        SpendingAmount.objects.create(
            profile=profile, category=self.dining, monthly_amount=Decimal('42'))

        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload('500.00'),
            content_type='application/json')

        amounts = list(profile.spending_amounts.all())
        self.assertEqual(len(amounts), 1)
        self.assertEqual(amounts[0].monthly_amount, Decimal('42'))

    def test_stale_session_anon_users_get_separate_profiles(self):
        """B1: removing the loose 'any anonymous profile with spending data'
        fallback means two different anonymous sessions never share a
        profile (and therefore never share a roadmap/share link)."""
        from django.test import Client
        client_a = Client()
        client_a.post(
            '/api/roadmaps/quick-recommendation/', self._payload('500.00'),
            content_type='application/json')
        session_a = client_a.session.session_key

        client_b = Client()
        client_b.post(
            '/api/roadmaps/quick-recommendation/', self._payload('700.00'),
            content_type='application/json')
        session_b = client_b.session.session_key

        self.assertNotEqual(session_a, session_b)
        profile_a = UserSpendingProfile.objects.get(session_key=session_a)
        profile_b = UserSpendingProfile.objects.get(session_key=session_b)
        self.assertNotEqual(profile_a.id, profile_b.id)


class LandingRedirectTests(TestCase):
    """Phase D: `/` skips the landing page and redirects straight to
    `/roadmap/` for visitors who already have a persisted Current Roadmap
    (auth or anon-via-session), and `/roadmap/`'s `has_current_roadmap`
    context flag drives the initial results-vs-builder view mode."""

    def setUp(self):
        # base.html renders a Google sign-in link for anon visitors; allauth
        # needs a SocialApp for provider_login_url to resolve.
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        app = SocialApp.objects.create(
            provider='google', name='Google', client_id='test', secret='test'
        )
        app.sites.add(Site.objects.get_current())

        self.user = User.objects.create_user(
            username='landing', email='landing@example.com', password='x')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        from cards.models import SpendingCategory
        self.dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        self.card = CreditCard.objects.create(
            name='Landing Card', slug='landing-card', issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)

    def _payload(self, amount='500.00'):
        return {
            'spending_amounts': {str(self.dining.id): amount},
            'user_cards': [],
            'max_recommendations': 1,
        }

    def test_landing_renders_for_visitor_with_no_roadmap(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

    def test_landing_does_not_create_profile_for_fresh_anon_visitor(self):
        """get_current_roadmap()'s read-only lookup must not fabricate a
        UserSpendingProfile/Roadmap for a visitor who has never generated
        one — a session cookie itself is already set on any full-page
        render in this app (messages framework), so that's not the
        guarantee to test; profile/roadmap creation is."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserSpendingProfile.objects.exists())
        self.assertFalse(Roadmap.objects.exists())

    def test_landing_redirects_for_auth_user_with_current_roadmap(self):
        self.client.force_login(self.user)
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

        response = self.client.get('/')
        self.assertRedirects(response, '/roadmap/')

    def test_landing_redirects_for_anon_session_with_current_roadmap(self):
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

        response = self.client.get('/')
        self.assertRedirects(response, '/roadmap/')

    def test_roadmap_page_has_current_roadmap_flag_false_for_new_visitor(self):
        response = self.client.get('/roadmap/')
        self.assertFalse(response.context['has_current_roadmap'])

    def test_roadmap_page_has_current_roadmap_flag_true_once_generated(self):
        self.client.force_login(self.user)
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

        response = self.client.get('/roadmap/')
        self.assertTrue(response.context['has_current_roadmap'])


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

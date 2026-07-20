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
              bonus_earned_days_ago=None, bonus_override=None):
        from datetime import timedelta
        from types import SimpleNamespace
        days = lambda n: self.today - timedelta(days=n) if n is not None else None
        return SimpleNamespace(
            card=card,
            opened_date=days(opened_days_ago),
            closed_date=days(closed_days_ago),
            bonus_earned_date=days(bonus_earned_days_ago),
            bonus_override=bonus_override,
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

    def test_bonus_override_false_unblocks_repeat_bonus(self):
        """User says they never actually earned the prior card's bonus
        (referred instead of applying, never activated) — the once-per-
        lifetime rule must not hold that against a new application."""
        from .eligibility import bonus_ineligibility
        gold = self._card('Amex Gold', self.amex)
        held_no_bonus = self._held(gold, opened_days_ago=1200,
                                   closed_days_ago=800, bonus_override=False)
        self.assertIsNone(bonus_ineligibility(gold, [held_no_bonus], self.today))
        # override=True (or unset) still blocks, same as today's behavior
        held_confirmed = self._held(gold, opened_days_ago=1200,
                                    closed_days_ago=800, bonus_override=True)
        self.assertIsNotNone(bonus_ineligibility(gold, [held_confirmed], self.today))

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

    def test_amex_5_card_limit_counts_open_cards_same_issuer(self):
        """Phase K: max_open_cards rule shape — a cap on OPEN cards, unlike
        the windowed max_new_cards rules above (no time bound)."""
        from .eligibility import application_block
        candidate = self._card('Amex Candidate', self.amex)
        held = [self._card(f'Amex {i}', self.amex) for i in range(5)]
        history = [self._held(c, opened_days_ago=1000) for c in held]
        self.assertIsNotNone(application_block(candidate, history, self.today))
        # At 4 open Amex cards, the 5th application goes through
        self.assertIsNone(application_block(candidate, history[:4], self.today))
        # A closed card doesn't count toward the open-card cap
        closed_history = [self._held(c, opened_days_ago=1000, closed_days_ago=10)
                          for c in held]
        self.assertIsNone(application_block(candidate, closed_history, self.today))
        # Other issuers' cards don't count toward Amex's own-issuer cap
        other = [self._held(self._card(f'Chase {i}', self.chase), opened_days_ago=1000)
                 for i in range(5)]
        self.assertIsNone(application_block(candidate, other, self.today))

    def test_sapphire_once_per_lifetime_application_blocks_even_after_close(self):
        """Phase K: application_eligibility once_per_lifetime is a stronger,
        forever block — distinct from application_family (blocks only while
        OPEN) and from bonus_eligibility (only zeroes the bonus)."""
        from .eligibility import application_block
        family_meta = {'application_eligibility': {
            'once_per_lifetime': True, 'family': 'chase-sapphire-personal',
            'label': 'Chase Sapphire application rule'}}
        reserve = self._card('Sapphire Reserve', self.chase, metadata=family_meta)
        preferred = self._card('Sapphire Preferred', self.chase, metadata=family_meta)
        # Never held either -> free to apply
        self.assertIsNone(application_block(preferred, [], self.today))
        # Held Reserve, even closed long ago -> Preferred is blocked forever
        closed = self._held(reserve, opened_days_ago=3000, closed_days_ago=2000)
        note = application_block(preferred, [closed], self.today)
        self.assertIsNotNone(note)
        self.assertIn('Chase Sapphire application rule', note)
        # A business Sapphire (no application_eligibility) never blocks
        business = self._card('Sapphire Reserve for Business', self.chase,
                              card_type='business')
        biz_held = self._held(business, opened_days_ago=3000)
        self.assertIsNone(application_block(preferred, [biz_held], self.today))

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


class MultiEntityEligibilityTests(TestCase):
    """Phase K2b: application eligibility moves from household-wide to
    per-entity — see RecommendationEngine._eligible_entity_for_card. Single-
    entity behavior is provably unchanged (existing EligibilityRuleTests +
    the JSON scenario sweep + Jamie Real cover that); these tests cover the
    genuinely new multi-entity behavior."""

    def setUp(self):
        from datetime import date
        from cards.models import ProfileEntity
        self.today = date.today()
        self.user = User.objects.create_user(username='household3', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.primary = self.profile.primary_entity()
        self.sam = ProfileEntity.objects.create(profile=self.profile, name='Sam')
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.chase = Issuer.objects.create(name='Chase', slug='chase')
        self.amex = Issuer.objects.create(name='American Express', slug='american-express')
        self.generic = Issuer.objects.create(name='Generic Bank', slug='generic-bank')

    def _card(self, name, issuer=None, card_type='personal', metadata=None):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=issuer or self.generic,
            card_type=card_type, signup_bonus_type=self.points,
            primary_reward_type=self.points, metadata=metadata or {})

    def _engine(self):
        from .recommendation_engine import RecommendationEngine
        return RecommendationEngine(self.profile)

    def test_two_entities_get_independent_524_budgets(self):
        """Primary alone is at 5/24, but Sam has a clean budget — the
        household as a whole is still eligible, via Sam."""
        from datetime import timedelta
        from cards.models import UserCard
        candidate = self._card('Chase Candidate', issuer=self.chase)
        for i in range(5):
            other = self._card(f'Primary Card {i}')
            UserCard.objects.create(
                user=self.user, card=other, owner=self.primary,
                opened_date=self.today - timedelta(days=100))

        engine = self._engine()
        self.assertTrue(engine._is_eligible_for_card(candidate))
        entity = engine._eligible_entity_for_card(candidate)
        self.assertEqual(entity.id, self.sam.id)

    def test_both_entities_at_524_blocks_card(self):
        from datetime import timedelta
        from cards.models import UserCard
        candidate = self._card('Chase Candidate 2', issuer=self.chase)
        for owner in (self.primary, self.sam):
            for i in range(5):
                other = self._card(f'{owner.name} Card {i}')
                UserCard.objects.create(
                    user=self.user, card=other, owner=owner,
                    opened_date=self.today - timedelta(days=100))

        engine = self._engine()
        self.assertFalse(engine._is_eligible_for_card(candidate))
        self.assertIsNone(engine._eligible_entity_for_card(candidate))

    def test_business_card_prefers_business_entity(self):
        from cards.models import ProfileEntity
        biz = ProfileEntity.objects.create(
            profile=self.profile, name='Acme LLC', kind='business')
        card = self._card('Biz Card', card_type='business')

        engine = self._engine()
        entity = engine._eligible_entity_for_card(card)
        self.assertEqual(entity.id, biz.id)

    def test_business_card_falls_back_to_primary_without_business_entity(self):
        """No declared business entity — sole-proprietor business cards are
        common, so fall back to the primary rather than strictly requiring
        one (this is what keeps Jamie Real's business cards working)."""
        card = self._card('Sole Prop Card', card_type='business')

        engine = self._engine()
        entity = engine._eligible_entity_for_card(card)
        self.assertEqual(entity.id, self.primary.id)

    def test_primary_first_tie_break_when_both_eligible(self):
        card = self._card('Either Card')

        engine = self._engine()
        entity = engine._eligible_entity_for_card(card)
        self.assertEqual(entity.id, self.primary.id)

    def test_bonus_note_evaluated_against_the_applying_entity(self):
        """Primary already holds this exact Amex card (open) — Sam doesn't.
        Sam is the one who'd apply, and the bonus note must be evaluated
        against SAM's clean history, not primary's (which would otherwise
        look Amex-lifetime-blocked)."""
        from datetime import timedelta
        from cards.models import UserCard
        card = self._card('Amex Card', issuer=self.amex)
        UserCard.objects.create(
            user=self.user, card=card, owner=self.primary,
            opened_date=self.today - timedelta(days=100))

        engine = self._engine()
        entity = engine._eligible_entity_for_card(card)
        self.assertEqual(entity.id, self.sam.id)
        self.assertIsNone(engine._bonus_ineligibility_note(card))

    def test_apply_as_attribution_end_to_end(self):
        """Primary is pinned at 5/24 (blocked); Sam is clean, so the apply
        recommendation for a new Chase card must be attributed to Sam."""
        from datetime import timedelta
        from cards.models import SpendingCategory, SpendingAmount, UserCard, RewardCategory
        from .models import Roadmap
        from .recommendation_engine import RecommendationEngine

        dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        SpendingAmount.objects.create(
            profile=self.profile, category=dining, monthly_amount=Decimal('1000'))

        for i in range(5):
            other = self._card(f'Primary Card {i}', issuer=self.chase)
            UserCard.objects.create(
                user=self.user, card=other, owner=self.primary,
                opened_date=self.today - timedelta(days=100))

        candidate = self._card('New Chase Card', issuer=self.chase, metadata={
            'reward_value_multiplier': 0.01,
            'signup_bonus': {'bonus_amount': 500, 'spending_requirement': 1000,
                              'time_limit_months': 3}})
        candidate.signup_bonus_amount = 500
        candidate.save()
        RewardCategory.objects.create(
            card=candidate, category=dining, reward_rate=Decimal('3.00'),
            reward_type=self.points)

        roadmap = Roadmap.objects.create(profile=self.profile, name='Test', max_recommendations=1)
        engine = RecommendationEngine(self.profile)
        recommendations = engine.generate_quick_recommendations(roadmap)

        applies = [r for r in recommendations if r['action'] == 'apply'
                   and r['card'].id == candidate.id]
        self.assertEqual(len(applies), 1)
        self.assertIn('apply_as', applies[0])
        self.assertEqual(applies[0]['apply_as']['name'], 'Sam')

    def test_apply_as_absent_for_single_entity_household(self):
        """Single-entity households (the common case) must not carry an
        apply_as key at all — old/anon payloads stay byte-identical."""
        from cards.models import SpendingCategory, SpendingAmount, ProfileEntity
        from .models import Roadmap
        from .recommendation_engine import RecommendationEngine

        self.sam.delete()  # back to a single-entity (primary-only) household
        self.assertEqual(ProfileEntity.objects.filter(profile=self.profile).count(), 1)

        dining = SpendingCategory.objects.create(name='Dining2', slug='dining2')
        SpendingAmount.objects.create(
            profile=self.profile, category=dining, monthly_amount=Decimal('1000'))
        candidate = self._card('Solo Chase Card', issuer=self.chase, metadata={
            'reward_value_multiplier': 0.01,
            'signup_bonus': {'bonus_amount': 500, 'spending_requirement': 1000,
                              'time_limit_months': 3}})
        candidate.signup_bonus_amount = 500
        candidate.save()
        from cards.models import RewardCategory
        RewardCategory.objects.create(
            card=candidate, category=dining, reward_rate=Decimal('3.00'),
            reward_type=self.points)

        roadmap = Roadmap.objects.create(profile=self.profile, name='Test2', max_recommendations=1)
        engine = RecommendationEngine(self.profile)
        recommendations = engine.generate_quick_recommendations(roadmap)

        for rec in recommendations:
            self.assertNotIn('apply_as', rec)


class SecondCopyApplyTests(TestCase):
    """Phase K2c: another household entity can apply for a card someone
    else already holds open (e.g. Player 2 applying for Player 1's held
    card). Valued on signup bonus alone — the held copy already earns the
    category rewards, so the reconciliation guard (headline == line items +
    bonus - fee) must hold with an all-zero line-item total."""

    def setUp(self):
        from cards.models import ProfileEntity
        self.user = User.objects.create_user(username='household4', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.primary = self.profile.primary_entity()
        self.sam = ProfileEntity.objects.create(profile=self.profile, name='Sam')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.generic = Issuer.objects.create(name='Generic Bank', slug='generic-bank')

    def _card(self, name, annual_fee=0, bonus_amount=500, requirement=1000):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=self.generic,
            annual_fee=Decimal(str(annual_fee)),
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback,
            signup_bonus_amount=bonus_amount,
            metadata={'reward_value_multiplier': 0.01,
                      'signup_bonus': {'bonus_amount': bonus_amount,
                                       'spending_requirement': requirement,
                                       'time_limit_months': 3}})

    def _spending(self, amount='1000'):
        from cards.models import SpendingCategory, SpendingAmount
        other = SpendingCategory.objects.create(name='Other', slug='other')
        SpendingAmount.objects.create(
            profile=self.profile, category=other, monthly_amount=Decimal(amount))

    def _generate(self, max_recommendations=2):
        from cards.models import UserCard
        from .models import Roadmap
        from .recommendation_engine import RecommendationEngine
        roadmap = Roadmap.objects.create(
            profile=self.profile, name='Test', max_recommendations=max_recommendations)
        engine = RecommendationEngine(self.profile)
        return engine.generate_quick_recommendations(roadmap)

    def test_single_entity_household_never_gets_second_copy(self):
        """Explicit no-op-equivalence guard: a lone entity is always the
        only (and therefore ineligible) candidate for its own held card, so
        no duplicate_copy apply is ever produced."""
        from cards.models import UserCard
        self.sam.delete()
        self._spending()
        card = self._card('Solo Household Card')
        UserCard.objects.create(user=self.user, card=card, owner=self.primary)

        recs = self._generate()
        duplicates = [r for r in recs if r['action'] == 'apply' and r['card'].id == card.id]
        self.assertEqual(duplicates, [])

    def test_second_copy_apply_is_bonus_only_and_reconciles(self):
        from cards.models import UserCard
        self._spending()
        card = self._card('Shared Household Card')
        UserCard.objects.create(user=self.user, card=card, owner=self.primary)

        recs = self._generate()
        second_copy = [r for r in recs if r['action'] == 'apply' and r['card'].id == card.id]
        self.assertEqual(len(second_copy), 1)
        rec = second_copy[0]

        self.assertTrue(rec.get('bonus_deferred') is False or 'bonus_deferred' not in rec)
        self.assertIn('apply_as', rec)
        self.assertEqual(rec['apply_as']['name'], 'Sam')
        self.assertEqual(float(rec['signup_bonus_value']), 500.0)
        # No category rewards double-counted — bonus (500) minus $0 fee.
        self.assertAlmostEqual(float(rec['estimated_rewards']), 500.0, places=2)
        line_total = sum(item['category_rewards'] for item in rec['rewards_breakdown'])
        self.assertEqual(line_total, 0)
        self.assertTrue(any(
            "already counted" in item.get('calculation', '')
            for item in rec['rewards_breakdown']))

        # The original keep is untouched and still present.
        keep = [r for r in recs if r['action'] == 'keep' and r['card'].id == card.id]
        self.assertEqual(len(keep), 1)

    def test_second_copy_skipped_when_no_other_entity_eligible(self):
        """Sam is also blocked (holds the family-blocking equivalent via
        being pinned at the issuer's own application cap) — no duplicate
        apply should be offered."""
        from datetime import timedelta, date
        from cards.models import UserCard
        self._spending()
        amex = Issuer.objects.create(name='American Express', slug='american-express')
        card = CreditCard.objects.create(
            name='Amex Shared Card', slug='amex-shared-card', issuer=amex,
            annual_fee=Decimal('0'), signup_bonus_type=self.cashback,
            primary_reward_type=self.cashback, signup_bonus_amount=500,
            metadata={'reward_value_multiplier': 0.01,
                      'signup_bonus': {'bonus_amount': 500,
                                       'spending_requirement': 1000,
                                       'time_limit_months': 3}})
        UserCard.objects.create(user=self.user, card=card, owner=self.primary)
        # Give Sam 5 open Amex cards -> at the 5-card cap, ineligible too.
        today = date.today()
        for i in range(5):
            other = CreditCard.objects.create(
                name=f'Sam Amex {i}', slug=f'sam-amex-{i}', issuer=amex,
                signup_bonus_type=self.cashback, primary_reward_type=self.cashback)
            UserCard.objects.create(
                user=self.user, card=other, owner=self.sam,
                opened_date=today - timedelta(days=100))

        recs = self._generate()
        duplicates = [r for r in recs if r['action'] == 'apply' and r['card'].id == card.id]
        self.assertEqual(duplicates, [])


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

    def _credit(self, card, spending_credit, value, currency='USD', times_per_year=1):
        from cards.models import CardCredit
        return CardCredit.objects.create(
            card=card, spending_credit=spending_credit,
            description=spending_credit.display_name, value=Decimal(str(value)),
            currency=currency, times_per_year=times_per_year)

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

    def test_calculate_smart_card_value_includes_credits(self):
        # Create a card with an annual fee and a credit
        card = self._card('Smart Card')
        card.annual_fee = Decimal('250.00')
        card.save()
        self._credit(card, self.lounge, 300)

        # Create the engine
        engine = self._engine()

        val_no_bonus = engine.optimizer.calculate_smart_card_value(card, signup_bonus=False)
        # Category rewards: 0, Credits: 300.0
        self.assertEqual(val_no_bonus, 300.0)

    def test_points_denominated_credit_discounted_not_face_value(self):
        """A 7,500-pt SOUTHWEST credit must value at its ~$105 redemption
        worth, not the raw $7,500 point count (the currency-valuation bug)."""
        from cards.models import PointsProgram, PointsValuation
        PointsProgram.objects.create(
            name='Southwest Rapid Rewards', slug='southwest_rapid_rewards',
            currency_code='SOUTHWEST')
        PointsValuation.objects.create(
            points_program=PointsProgram.objects.get(slug='southwest_rapid_rewards'),
            user=None, value=Decimal('0.0140'))

        card = self._card('Southwest Points Card')
        self._credit(card, self.lounge, 7500, currency='SOUTHWEST')

        engine = self._engine()
        entries = engine._counted_card_credits(card)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['annual_value'], 105.0)

        allocation = engine._allocate_portfolio_credits([card])
        self.assertEqual(allocation[card.id][0], 105.0)

    def test_usd_credit_still_equals_face_value(self):
        """Regression guard: rate must be exactly 1.0 for USD, unaffected by
        the currency-valuation change."""
        card = self._card('USD Credit Card')
        self._credit(card, self.lounge, 300)

        engine = self._engine()
        entries = engine._counted_card_credits(card)
        self.assertEqual(entries[0]['annual_value'], 300.0)

    def test_pays_for_itself_flag_in_recommendations(self):
        from cards.models import SpendingAmount, SpendingCategory
        from roadmaps.models import Roadmap

        travel = SpendingCategory.objects.get(slug='travel')
        SpendingAmount.objects.create(
            profile=self.profile, category=travel,
            monthly_amount=Decimal('2000'))

        # Set up a card that pays for itself (credits >= fee)
        card_pays = self._card('Pays Card')
        card_pays.annual_fee = Decimal('200.00')
        card_pays.signup_bonus_amount = 50000
        card_pays.metadata = {
            'signup_bonus': {
                'spending_requirement': 1000,
                'time_limit_months': 3,
                'bonus_value': 500.0,
            }
        }
        card_pays.save()
        self._credit(card_pays, self.lounge, 250)

        # Set up a card that does NOT pay for itself (credits < fee)
        card_not_pays = self._card('Not Pays Card')
        card_not_pays.annual_fee = Decimal('300.00')
        card_not_pays.signup_bonus_amount = 50000
        card_not_pays.metadata = {
            'signup_bonus': {
                'spending_requirement': 1000,
                'time_limit_months': 3,
                'bonus_value': 500.0,
            }
        }
        card_not_pays.save()
        self._credit(card_not_pays, self.uber_eats, 100)

        roadmap = Roadmap.objects.create(profile=self.profile, max_recommendations=5)
        engine = self._engine()
        recs = engine.generate_quick_recommendations(roadmap)

        rec_pays = next((r for r in recs if r['card'].id == card_pays.id), None)
        rec_not_pays = next((r for r in recs if r['card'].id == card_not_pays.id), None)

        self.assertIsNotNone(rec_pays)
        self.assertIsNotNone(rec_not_pays)
        self.assertTrue(rec_pays['pays_for_itself'])
        self.assertFalse(rec_not_pays['pays_for_itself'])


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


class RoadmapSharingTests(TestCase):
    """C1-C4: sharing a Current Roadmap mirrors profile sharing
    (UserSpendingProfile.share_uuid), but is anon-capable — a session-owned
    roadmap can be made public and read back logged-out, unlike profile
    sharing which requires auth."""

    def setUp(self):
        # shared_roadmap.html extends base.html, which renders a Google
        # sign-in link for anon visitors; allauth needs a SocialApp for
        # provider_login_url to resolve (see LandingRedirectTests).
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        app = SocialApp.objects.create(
            provider='google', name='Google', client_id='test', secret='test'
        )
        app.sites.add(Site.objects.get_current())

        from cards.models import SpendingCategory
        self.user = User.objects.create_user(
            username='sharer', email='sharer@example.com', password='x')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        self.card = CreditCard.objects.create(
            name='Share Card', slug='share-card', issuer=self.issuer,
            signup_bonus_type=self.cashback, primary_reward_type=self.cashback)

    def _payload(self, amount='500.00'):
        return {
            'spending_amounts': {str(self.dining.id): amount},
            'user_cards': [],
            'max_recommendations': 1,
        }

    def _generate(self, client):
        return client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

    def test_get_share_with_no_current_roadmap_returns_private_default(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/roadmaps/current/share/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['privacy_setting'], 'private')
        self.assertFalse(data['is_public'])

    def test_post_public_mints_share_uuid_and_url(self):
        self.client.force_login(self.user)
        self._generate(self.client)

        response = self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_public'])
        self.assertIn('share_uuid', data)
        self.assertIn('shareable_url', data)

        roadmap = Roadmap.objects.get(profile__user=self.user, name='Current Roadmap')
        self.assertTrue(roadmap.is_public)
        self.assertIsNotNone(roadmap.share_uuid)
        self.assertEqual(str(roadmap.share_uuid), data['share_uuid'])

    def test_post_share_404s_with_no_current_roadmap(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_post_share_400s_on_invalid_privacy_setting(self):
        self.client.force_login(self.user)
        self._generate(self.client)
        response = self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'nonsense'},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_private_roadmap_404s_on_page_and_data_endpoint(self):
        self.client.force_login(self.user)
        self._generate(self.client)
        roadmap = Roadmap.objects.get(profile__user=self.user, name='Current Roadmap')
        roadmap.generate_share_uuid()  # mint a uuid without making it public

        page_response = self.client.get(f'/roadmap/shared/{roadmap.share_uuid}/')
        self.assertEqual(page_response.status_code, 404)
        data_response = self.client.get(f'/api/roadmaps/shared/{roadmap.share_uuid}/')
        self.assertEqual(data_response.status_code, 404)

    def test_public_roadmap_renders_for_logged_out_client(self):
        self.client.force_login(self.user)
        self._generate(self.client)
        self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        roadmap = Roadmap.objects.get(profile__user=self.user, name='Current Roadmap')

        from django.test import Client
        logged_out = Client()
        page_response = logged_out.get(f'/roadmap/shared/{roadmap.share_uuid}/')
        self.assertEqual(page_response.status_code, 200)

        data_response = logged_out.get(f'/api/roadmaps/shared/{roadmap.share_uuid}/')
        self.assertEqual(data_response.status_code, 200)
        data = data_response.json()
        self.assertIn('recommendations', data)
        self.assertIn('generated_at', data)
        self.assertEqual(data['owner_display_name'], 'sharer')

    def test_regenerate_keeps_the_same_share_uuid(self):
        self.client.force_login(self.user)
        self._generate(self.client)
        self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        original_uuid = Roadmap.objects.get(
            profile__user=self.user, name='Current Roadmap').share_uuid

        self._generate(self.client)  # regenerate
        roadmap = Roadmap.objects.get(profile__user=self.user, name='Current Roadmap')
        self.assertEqual(roadmap.share_uuid, original_uuid)
        self.assertTrue(roadmap.is_public)

    def test_flipping_to_private_kills_the_link(self):
        self.client.force_login(self.user)
        self._generate(self.client)
        self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        roadmap = Roadmap.objects.get(profile__user=self.user, name='Current Roadmap')
        share_uuid = roadmap.share_uuid

        response = self.client.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'private'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_public'])

        from django.test import Client
        logged_out = Client()
        data_response = logged_out.get(f'/api/roadmaps/shared/{share_uuid}/')
        self.assertEqual(data_response.status_code, 404)

    def test_anon_session_owned_roadmap_can_be_shared_and_read_logged_out(self):
        """The deliberate divergence from profile sharing: no auth required
        to share, since a session-owned Current Roadmap already exists."""
        from django.test import Client
        anon = Client()
        self._generate(anon)

        share_response = anon.post(
            '/api/roadmaps/current/share/', {'privacy_setting': 'public'},
            content_type='application/json')
        self.assertEqual(share_response.status_code, 200)
        share_uuid = share_response.json()['share_uuid']

        other_client = Client()
        data_response = other_client.get(f'/api/roadmaps/shared/{share_uuid}/')
        self.assertEqual(data_response.status_code, 200)
        self.assertEqual(data_response.json()['owner_display_name'], 'A Credit Card Guru user')


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
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertTrue(response.context['has_roadmap'])
        self.assertTrue(response.context['user_authenticated'])

    def test_landing_redirects_for_anon_session_with_current_roadmap(self):
        self.client.post(
            '/api/roadmaps/quick-recommendation/', self._payload(),
            content_type='application/json')

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertTrue(response.context['has_roadmap'])
        self.assertFalse(response.context['user_authenticated'])

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


class RoadmapAnalysisPayloadTests(TestCase):
    """Phase I: portfolio_summary.category_allocation (the full per-category
    -> per-card allocation, superseding the single-winner category_optimization
    for the new matrix view) and per-card redemption guidance both reach the
    quick-recommendation JSON payload, and the allocation reconciles with the
    existing per-card rewards_breakdown line for the same category."""

    def setUp(self):
        from cards.models import SpendingCategory, RewardCategory
        self.user = User.objects.create_user(
            username='analyst', email='analyst@example.com', password='x')
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.issuer = Issuer.objects.create(name='Analysis Bank', slug='analysis-bank')
        self.dining = SpendingCategory.objects.create(name='Dining', slug='dining')
        self.card = CreditCard.objects.create(
            name='UR Dining Card', slug='ur-dining-card', issuer=self.issuer,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            metadata={'points_program': 'chase_ultimate_rewards', 'reward_value_multiplier': 0.01})
        RewardCategory.objects.create(
            card=self.card, category=self.dining, reward_rate=Decimal('3.00'),
            reward_type=self.points)

    def _generate(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {'spending_amounts': {str(self.dining.id): '500.00'},
             'user_cards': [], 'max_recommendations': 1},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_category_allocation_reaches_payload_and_reconciles(self):
        data = self._generate()
        allocation = data['portfolio_summary']['category_allocation']
        dining_entries = [e for e in allocation if e['category_slug'] == 'dining']
        self.assertEqual(len(dining_entries), 1)
        entry = dining_entries[0]
        self.assertEqual(entry['card_id'], self.card.id)
        self.assertEqual(entry['card_name'], self.card.name)
        self.assertEqual(entry['rate'], 3.0)
        self.assertAlmostEqual(entry['annual_spend'], 500 * 12)
        self.assertFalse(entry['uncovered'])

        # Reconciles with the per-card breakdown line for the same category
        rec = next(r for r in data['recommendations'] if r['card']['id'] == self.card.id)
        breakdown_line = next(
            b for b in rec['rewards_breakdown'] if b['type'] == 'reward_category')
        self.assertAlmostEqual(entry['annual_rewards'], breakdown_line['category_rewards'], places=2)

    def test_redemption_guidance_reaches_payload_for_curated_program(self):
        data = self._generate()
        rec = next(r for r in data['recommendations'] if r['card']['id'] == self.card.id)
        redemption = rec['card']['redemption']
        self.assertEqual(redemption['program_label'], 'Chase Ultimate Rewards')
        self.assertTrue(redemption['transfer_partners'])
        self.assertEqual(redemption['value_per_point'], 0.015)


class RedemptionGuidanceTests(TestCase):
    """Phase I: roadmaps/redemption.py's curated-lookup-with-fallback logic,
    independent of the recommendation engine."""

    def setUp(self):
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.cashback = RewardType.objects.create(name='Cashback', slug='cashback')
        self.issuer = Issuer.objects.create(name='Redemption Bank', slug='redemption-bank')

    def _card(self, name, reward_type, metadata=None, url=''):
        from django.utils.text import slugify
        return CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=self.issuer,
            signup_bonus_type=reward_type, primary_reward_type=reward_type,
            metadata=metadata or {}, url=url)

    def test_curated_program_returns_chase_guidance(self):
        from .redemption import redemption_guidance_for
        card = self._card('Curated Chase Card', self.points,
                           metadata={'points_program': 'chase_ultimate_rewards'})
        guidance = redemption_guidance_for(card)
        self.assertEqual(guidance['program_label'], 'Chase Ultimate Rewards')
        self.assertIn('United MileagePlus', guidance['transfer_partners'])
        self.assertEqual(guidance['value_per_point'], 0.015)

    def test_cashback_card_gets_generic_cashback_note(self):
        from .redemption import redemption_guidance_for
        card = self._card('Plain Cashback Card', self.cashback)
        guidance = redemption_guidance_for(card)
        self.assertIsNone(guidance['program_label'])
        self.assertEqual(guidance['transfer_partners'], [])
        self.assertIn('statement credit', guidance['note'])

    def test_uncurated_points_card_gets_generic_portal_note(self):
        from .redemption import redemption_guidance_for
        card = self._card('Uncurated Points Card', self.points,
                           url='https://issuer.example.com/rewards')
        guidance = redemption_guidance_for(card)
        self.assertIsNone(guidance['program_label'])
        self.assertEqual(guidance['portal_url'], 'https://issuer.example.com/rewards')
        self.assertNotIn('statement credit', guidance['note'])

    def test_custom_user_valuation_override(self):
        from .redemption import redemption_guidance_for
        from django.contrib.auth.models import User
        from cards.models import PointsProgram, PointsValuation

        # Create points program
        program = PointsProgram.objects.create(
            name='Test Ultimate Rewards',
            slug='chase_ultimate_rewards',
            portal_url='https://www.chase.com',
            transfer_partners=['Hyatt', 'United'],
            note='Test note'
        )

        card = self._card('Chase Card', self.points,
                           metadata={'points_program': 'chase_ultimate_rewards'})
        # Verify the program was linked to the card automatically via save()
        self.assertEqual(card.points_program, program)

        # Create system default valuation
        PointsValuation.objects.create(
            points_program=program,
            user=None,
            value=0.0150
        )

        # Create user and user valuation override
        user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        PointsValuation.objects.create(
            points_program=program,
            user=user,
            value=0.0200
        )

        # Test anonymous/no-user guidance returns system default (0.015)
        guidance_anon = redemption_guidance_for(card)
        self.assertEqual(guidance_anon['value_per_point'], 0.015)

        # Test authenticated user guidance returns user override (0.020)
        guidance_user = redemption_guidance_for(card, user=user)
        self.assertEqual(guidance_user['value_per_point'], 0.020)


class ExpenseRecommenderTests(TestCase):
    """Phase N: one-off upcoming-expense mode
    (roadmaps/engine/calculators/expense.py) — a parallel, read-only path
    that never touches spending_amounts or the portfolio reconciliation
    guard. Its value for every card is a visible sum (signup_bonus_value +
    category_rewards - effective_annual_fee), so the core assertion across
    these tests is that the sum always holds exactly."""

    def setUp(self):
        from cards.models import SpendingCategory
        self.user = User.objects.create_user(
            username='expense', email='expense@example.com', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.travel = SpendingCategory.objects.create(name='Travel', slug='travel')
        self.other = SpendingCategory.objects.create(name='Other', slug='other')
        # No SpendingAmount rows -> $0/mo recurring spend for every test here
        # unless a test creates one explicitly.

    def _card(self, name, requirement=0, time_months=3, bonus_amount=500,
              rate=Decimal('3.00'), max_annual_spend=None, category=None):
        from django.utils.text import slugify
        from cards.models import RewardCategory
        card = CreditCard.objects.create(
            name=name, slug=slugify(name), issuer=self.issuer,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            signup_bonus_amount=bonus_amount,
            metadata={'reward_value_multiplier': 0.01,
                      'signup_bonus': {'bonus_amount': bonus_amount,
                                        'spending_requirement': requirement,
                                        'time_limit_months': time_months}})
        RewardCategory.objects.create(
            card=card, category=category or self.travel, reward_rate=rate,
            reward_type=self.points, max_annual_spend=max_annual_spend)
        return card

    def _roadmap(self, max_recommendations=5):
        return Roadmap.objects.create(
            profile=self.profile, name='Expense Test', max_recommendations=max_recommendations)

    def _engine(self):
        from .recommendation_engine import RecommendationEngine
        return RecommendationEngine(self.profile)

    def test_lump_sum_makes_bonus_reachable_with_zero_monthly_spend(self):
        """The core new behavior: a $10k expense satisfies a $4k minimum
        spend even though the household has no recurring spending at all —
        something the existing monthly-projection check can't do."""
        card = self._card('Travel Card', requirement=4000, time_months=3)
        engine = self._engine()

        reachable, required, months = engine.bonus_capacity_manager \
            .can_meet_signup_requirement_with_expense(card, 10000)
        self.assertTrue(reachable)
        self.assertEqual(required, 4000.0)
        self.assertEqual(months, 3.0)

        # The existing monthly-projection reachability check would say no —
        # confirms this is genuinely new behavior, not already covered.
        self.assertFalse(engine._can_meet_signup_requirement(card))

        result = engine._recommend_for_expense(10000, 'travel', self._roadmap())
        self.assertTrue(result['apply'])
        top = result['apply'][0]
        self.assertEqual(top['card'].id, card.id)
        self.assertGreater(top['signup_bonus_value'], 0)

    def test_expense_below_requirement_does_not_reach_bonus(self):
        card = self._card('Unreachable Card', requirement=20000, time_months=3)
        engine = self._engine()
        reachable, required, months = engine.bonus_capacity_manager \
            .can_meet_signup_requirement_with_expense(card, 5000)
        self.assertFalse(reachable)
        self.assertEqual(
            engine.bonus_capacity_manager.get_signup_bonus_value_for_expense(card, 5000),
            0.0)

    def test_value_for_expense_reconciles(self):
        self._card('Reconcile Card', requirement=1000, time_months=3)
        engine = self._engine()
        result = engine._recommend_for_expense(5000, 'travel', self._roadmap())
        self.assertTrue(result['apply'])
        for item in result['apply']:
            self.assertAlmostEqual(
                item['value_for_expense'],
                item['signup_bonus_value'] + item['category_rewards'] - item['effective_annual_fee'],
                places=6)

    def test_max_annual_spend_caps_the_lump_then_spills_to_base_rate(self):
        """$3,000 on a card with a 5x travel rate capped at $1,000: the
        capped $1,000 earns 5x, the remaining $2,000 spills to the 1x base
        rate — not 5x on the full amount, not 0 on the overflow."""
        from cards.models import RewardCategory
        card = self._card('Capped Travel Card', rate=Decimal('5.00'),
                           max_annual_spend=Decimal('1000'))
        RewardCategory.objects.create(
            card=card, category=self.other, reward_rate=Decimal('1.00'),
            reward_type=self.points)

        engine = self._engine()
        rewards, rate, multiplier = engine.expense_recommender._category_rewards_for_expense(
            card, 3000, 'travel', None)

        self.assertEqual(rate, 5.0)
        self.assertAlmostEqual(rewards, (1000 * 5 * 0.01) + (2000 * 1 * 0.01))

    def test_best_owned_picks_highest_category_rate_with_no_bonus_or_fee(self):
        from datetime import date
        from cards.models import UserCard
        low_card = self._card('Low Rate Card', rate=Decimal('1.00'))
        high_card = self._card('High Rate Card', rate=Decimal('4.00'))
        UserCard.objects.create(user=self.user, card=low_card, opened_date=date(2023, 1, 1))
        UserCard.objects.create(user=self.user, card=high_card, opened_date=date(2023, 1, 1))

        engine = self._engine()
        result = engine._recommend_for_expense(2000, 'travel', self._roadmap())

        self.assertIsNotNone(result['best_owned'])
        self.assertEqual(result['best_owned']['card'].id, high_card.id)
        self.assertEqual(result['best_owned']['signup_bonus_value'], 0.0)
        self.assertEqual(result['best_owned']['effective_annual_fee'], 0.0)
        # Already-owned cards must not also appear in the apply list
        applied_ids = [c['card'].id for c in result['apply']]
        self.assertNotIn(high_card.id, applied_ids)
        self.assertNotIn(low_card.id, applied_ids)

    def test_no_category_falls_back_to_base_rate_only(self):
        """category_slug=None ('general purchase') must not match a card's
        specific-category rate — only its base rate counts."""
        from cards.models import RewardCategory
        card = self._card('Base Only Card', rate=Decimal('5.00'))  # travel-only, 5x
        RewardCategory.objects.create(
            card=card, category=self.other, reward_rate=Decimal('2.00'),
            reward_type=self.points)

        engine = self._engine()
        rewards, rate, _ = engine.expense_recommender._category_rewards_for_expense(
            card, 1000, None, None)
        self.assertEqual(rate, 2.0)
        self.assertAlmostEqual(rewards, 1000 * 2 * 0.01)


class ExpenseRecommendationResponseTests(TestCase):
    """The API surface for Phase N: expense_recommendation is present only
    when the request actually posted an 'expense' — old/plain payloads must
    stay byte-identical."""

    def setUp(self):
        from cards.models import SpendingCategory
        self.user = User.objects.create_user(
            username='expenseapi', email='expenseapi@example.com', password='x')
        self.profile = UserSpendingProfile.objects.create(user=self.user)
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.issuer = Issuer.objects.create(name='Generic Bank', slug='generic-bank')
        self.travel = SpendingCategory.objects.create(name='Travel', slug='travel')

    def test_response_omits_expense_key_when_not_requested(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {'max_recommendations': 1},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('expense_recommendation', response.json())

    def test_response_includes_expense_recommendation_when_requested(self):
        from django.utils.text import slugify
        from cards.models import RewardCategory
        card = CreditCard.objects.create(
            name='API Expense Card', slug=slugify('API Expense Card'), issuer=self.issuer,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            signup_bonus_amount=500,
            metadata={'reward_value_multiplier': 0.01,
                      'signup_bonus': {'bonus_amount': 500, 'spending_requirement': 1000,
                                        'time_limit_months': 3}})
        RewardCategory.objects.create(
            card=card, category=self.travel, reward_rate=Decimal('3.00'), reward_type=self.points)

        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {'max_recommendations': 1,
             'expense': {'amount': 5000, 'category_id': self.travel.id}},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('expense_recommendation', data)
        expense = data['expense_recommendation']
        self.assertEqual(expense['amount'], 5000.0)
        self.assertEqual(expense['category_slug'], 'travel')
        self.assertTrue(expense['apply'])
        top = expense['apply'][0]
        self.assertAlmostEqual(
            top['value_for_expense'],
            top['signup_bonus_value'] + top['category_rewards'] - top['effective_annual_fee'],
            places=2)


class EasyModeSpendingTests(TestCase):
    """Tests for Phase O: Category-less 'easy mode' spending"""

    def setUp(self):
        from cards.models import SpendingCategory, RewardCategory
        self.user = User.objects.create_user(
            username='easymoder', email='easymoder@example.com', password='x')
        self.points = RewardType.objects.create(name='Points', slug='points')
        self.issuer = Issuer.objects.create(name='Easy Bank', slug='easy-bank')
        
        # 'other' category is used for fallback
        self.other = SpendingCategory.objects.create(name='Other Spending', slug='other')
        
        self.card = CreditCard.objects.create(
            name='Flat Rate Card', slug='flat-rate-card', issuer=self.issuer,
            signup_bonus_type=self.points, primary_reward_type=self.points,
            metadata={'reward_value_multiplier': 0.01}
        )
        RewardCategory.objects.create(
            card=self.card, category=self.other, reward_rate=Decimal('2.00'),
            reward_type=self.points)

    def test_monthly_easy_mode_spending(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {
                'easy_mode_spending': {'amount': 3000.0, 'interval': 'monthly'},
                'user_cards': [],
                'max_recommendations': 1
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify total estimated rewards reconciles to:
        # $3000/mo * 12 mo = $36000 annual spend
        # $36000 * 2% reward rate = 72000 points
        # 72000 points * 0.01 reward value multiplier = $720.00
        # Since it is a newly applied card, total value = signup bonus + annual rewards - fee.
        # But this card has 0 signup bonus, so estimated value = $720.00.
        self.assertEqual(len(data['recommendations']), 1)
        rec = data['recommendations'][0]
        self.assertAlmostEqual(float(rec['estimated_rewards']), 720.00, places=2)

    def test_yearly_easy_mode_spending(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/roadmaps/quick-recommendation/',
            {
                'easy_mode_spending': {'amount': 48000.0, 'interval': 'yearly'},
                'user_cards': [],
                'max_recommendations': 1
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # $48000/yr annual spend
        # $48000 * 2% reward rate = 96000 points
        # 96000 points * 0.01 multiplier = $960.00
        self.assertEqual(len(data['recommendations']), 1)
        rec = data['recommendations'][0]
        self.assertAlmostEqual(float(rec['estimated_rewards']), 960.00, places=2)

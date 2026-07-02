"""
Django management command to run individual test scenarios.

Usage:
    python manage.py run_scenario "Young Professional - Dining Focus"
    python manage.py run_scenario --all
    python manage.py run_scenario --list
"""

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

from cards.models import (
    Issuer, RewardType, SpendingCategory, CreditCard, RewardCategory,
    UserSpendingProfile, SpendingAmount, UserCard
)
from roadmaps.models import Roadmap
from roadmaps.recommendation_engine import RecommendationEngine


class Command(BaseCommand):
    help = 'Run credit card recommendation scenarios from JSON file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'scenario_name',
            nargs='?',
            type=str,
            help='Name of the scenario to run'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all scenarios'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available scenarios'
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='JSON file or directory containing scenarios (default: auto-detect)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed breakdown information'
        )
        parser.add_argument(
            '--explain',
            action='store_true',
            help='Show the full line-item math for every recommendation, '
                 'with a reconciliation line you can check by hand'
        )
    
    def handle(self, *args, **options):
        # Get project root directory (go up from cards/management/commands/ to project root)
        # Import scenario loader
        from cards.scenario_loader import ScenarioLoader
        
        try:
            if options['file']:
                # Use specific file/directory path
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                full_path = os.path.join(project_root, options['file'])
                data = ScenarioLoader.load_scenarios(full_path)
            else:
                # Auto-detect scenarios
                data = ScenarioLoader.load_scenarios()
            
            scenarios = data.get('scenarios', [])
        except FileNotFoundError as e:
            raise CommandError(f'Scenarios not found: {e}')
        
        if not scenarios:
            raise CommandError('No scenarios found in file')
        
        if options['list']:
            self.list_scenarios(scenarios)
            return
        
        # Set up test data
        self.setup_test_data()
        
        verbose = options['verbose'] or options['explain']
        self.explain = options['explain']

        if options['all']:
            self.run_all_scenarios(scenarios, verbose)
        elif options['scenario_name']:
            self.run_single_scenario(scenarios, options['scenario_name'], verbose)
        else:
            raise CommandError('Please specify a scenario name or use --all or --list')
    
    def list_scenarios(self, scenarios):
        """List all available scenarios."""
        self.stdout.write(self.style.SUCCESS(f'Found {len(scenarios)} scenarios:'))
        self.stdout.write('')
        
        for i, scenario in enumerate(scenarios, 1):
            self.stdout.write(f'{i}. {scenario["name"]}')
            if 'description' in scenario:
                self.stdout.write(f'   {scenario["description"]}')
            
            # Show spending summary
            spending = scenario.get('user_profile', {}).get('spending', {})
            total_spending = sum(spending.values())
            self.stdout.write(f'   Monthly Spending: ${total_spending:,.0f}')
            
            # Show number of cards
            num_cards = len(scenario.get('available_cards', []))
            num_owned = len(scenario.get('owned_cards', []))
            self.stdout.write(f'   Cards: {num_cards} available, {num_owned} owned')
            self.stdout.write('')
    
    def run_all_scenarios(self, scenarios, verbose=False):
        """Run all scenarios."""
        self.stdout.write(self.style.SUCCESS(f'Running {len(scenarios)} scenarios...'))
        self.stdout.write('')
        
        for scenario in scenarios:
            self.run_scenario(scenario, verbose)
            self.stdout.write('')
    
    def run_single_scenario(self, scenarios, scenario_name, verbose=False):
        """Run a single scenario by name."""
        scenario = None
        for s in scenarios:
            if s['name'] == scenario_name:
                scenario = s
                break
        
        if not scenario:
            available_names = [s['name'] for s in scenarios]
            raise CommandError(f'Scenario "{scenario_name}" not found. Available scenarios: {", ".join(available_names)}')
        
        self.run_scenario(scenario, verbose)
    
    def run_scenario(self, scenario_data, verbose=False):
        """Run a single scenario and display results."""
        self.stdout.write(self.style.HTTP_INFO(f'=== {scenario_data["name"]} ==='))
        
        if 'description' in scenario_data:
            self.stdout.write(f'Description: {scenario_data["description"]}')
            self.stdout.write('')
        
        # Create the scenario
        profile, created_cards = self.create_test_scenario(scenario_data)

        # Optional strategy preset: its filters narrow the card pool and its
        # max_recommendations caps new applications (expected count stays a
        # pure assertion for strategy scenarios). A top-level
        # "max_recommendations" beats both — needed when a scenario must
        # allow MORE applies than it expects (e.g. bonus-capacity tests
        # prove cards get deferred, which a count-derived cap would mask).
        from roadmaps.strategies import resolve_scenario_strategy, apply_strategy_to_roadmap
        strategy = resolve_scenario_strategy(scenario_data)
        if strategy:
            self.stdout.write(f'Strategy: {strategy["name"]}')
        if 'max_recommendations' in scenario_data:
            max_recommendations = scenario_data['max_recommendations']
        elif strategy:
            max_recommendations = strategy['max_recommendations']
        else:
            max_recommendations = scenario_data.get('expected_recommendations', {}).get('count', 5)

        # Create roadmap
        roadmap = Roadmap.objects.create(
            profile=profile,
            name=f"Scenario: {scenario_data['name']}",
            max_recommendations=max_recommendations
        )
        apply_strategy_to_roadmap(roadmap, strategy)

        # Generate recommendations
        engine = RecommendationEngine(profile, strategy=strategy)
        recommendations = engine.generate_quick_recommendations(roadmap)
        
        # Display results
        self.display_results(scenario_data, recommendations, verbose)
        
        # Cleanup: the scenario user (cascades its profile/cards/spending)
        # AND any fixture cards this run created in the database.
        profile.user.delete()
        for card in getattr(self, 'created_fixture_cards', []):
            card.delete()
    
    def display_results(self, scenario_data, recommendations, verbose=False):
        """Display scenario results."""
        # Show spending profile
        spending = scenario_data['user_profile']['spending']
        total_monthly = sum(spending.values())
        
        self.stdout.write(f'Monthly Spending Profile (${total_monthly:,.0f} total):')
        for category, amount in spending.items():
            percentage = (amount / total_monthly) * 100
            self.stdout.write(f'  • {category.title()}: ${amount:,.0f} ({percentage:.1f}%)')
        self.stdout.write('')
        
        # Show owned cards (entries are slugs or history dicts)
        owned_cards = scenario_data.get('owned_cards', [])
        if owned_cards:
            def describe(entry):
                if isinstance(entry, dict):
                    parts = [entry['card']]
                    if entry.get('opened_date'):
                        parts.append(f"opened {entry['opened_date']}")
                    if entry.get('closed_date'):
                        parts.append(f"closed {entry['closed_date']}")
                    return ' '.join(parts)
                return entry
            self.stdout.write(
                f'Currently Owned Cards: {", ".join(describe(e) for e in owned_cards)}')
            self.stdout.write('')
        
        # Show recommendations
        if not recommendations:
            self.stdout.write(self.style.WARNING('No recommendations generated.'))
            return
        
        total_value = sum(float(rec['estimated_rewards']) for rec in recommendations)
        self.stdout.write(self.style.SUCCESS(f'Generated {len(recommendations)} recommendations (Total Value: ${total_value:.2f}):'))
        self.stdout.write('')
        
        for i, rec in enumerate(recommendations, 1):
            action_style = self.style.SUCCESS if rec['action'] == 'apply' else self.style.WARNING
            self.stdout.write(action_style(f'{i}. {rec["action"].upper()}: {rec["card"].name}'))
            self.stdout.write(f'   Annual Fee: ${rec["card"].annual_fee}')
            self.stdout.write(f'   Estimated Annual Value: ${rec["estimated_rewards"]}')
            self.stdout.write(f'   Reasoning: {rec["reasoning"]}')

            if verbose and rec.get('rewards_breakdown'):
                self.stdout.write('   Detailed Breakdown:')
                for breakdown in rec['rewards_breakdown']:
                    self.stdout.write(f'     • {breakdown["category_name"]}: {breakdown["calculation"]}')

            if getattr(self, 'explain', False):
                self.print_reconciliation(rec)
            self.stdout.write('')
        
        # Validate against expectations if provided
        expected = scenario_data.get('expected_recommendations', {})
        if expected:
            self.validate_expectations(recommendations, expected, scenario_data['name'])
    
    def print_reconciliation(self, rec):
        """Print the check-it-by-hand math for one recommendation."""
        card = rec['card']
        breakdown = rec.get('rewards_breakdown', [])
        line_total = sum(float(item.get('category_rewards', 0)) for item in breakdown)
        signup = float(rec.get('signup_bonus_value', 0) or 0)
        annual_fee = float(card.annual_fee)
        fee_waived = bool(card.metadata and card.metadata.get('annual_fee_waived_first_year'))
        fee = 0 if (rec['action'] == 'apply' and fee_waived) else annual_fee
        expected_total = line_total + signup - fee
        estimated = float(rec['estimated_rewards'])

        multiplier = rec.get('reward_value_multiplier')
        if multiplier:
            self.stdout.write(f'   Point valuation: {multiplier * 100:.2f}¢ per point/mile')
        parts = [f'line items ${line_total:,.2f}']
        if signup:
            parts.append(f'signup ${signup:,.2f}')
        parts.append(f'fee -${fee:,.2f}' + (' (waived)' if fee == 0 and annual_fee else ''))
        check = '✓' if abs(estimated - expected_total) < 1 else f'✗ MISMATCH (headline ${estimated:,.2f})'
        self.stdout.write(f'   Check: {" + ".join(parts)} = ${expected_total:,.2f} {check}')
        if rec.get('first_year_value') is not None and rec.get('ongoing_value') is not None:
            if abs(float(rec['first_year_value']) - float(rec['ongoing_value'])) >= 1:
                self.stdout.write(
                    f'   First year: ${float(rec["first_year_value"]):,.2f} | '
                    f'Ongoing: ${float(rec["ongoing_value"]):,.2f}/yr')

    def validate_expectations(self, recommendations, expected, scenario_name):
        """Validate recommendations against expected results."""
        issues = []
        
        # Check count
        expected_count = expected.get('count')
        if expected_count and len(recommendations) != expected_count:
            issues.append(f'Expected {expected_count} recommendations, got {len(recommendations)}')
        
        # Check actions
        expected_actions = expected.get('actions', [])
        actual_actions = [rec['action'] for rec in recommendations]
        for action in expected_actions:
            if action not in actual_actions:
                issues.append(f'Expected action "{action}" not found')
        
        # Check minimum value
        min_value = expected.get('min_total_value')
        if min_value:
            total_value = sum(float(rec['estimated_rewards']) for rec in recommendations)
            if total_value < min_value:
                issues.append(f'Total value ${total_value:.2f} below minimum ${min_value}')
        
        # Check must-include cards
        must_include = expected.get('must_include_cards', [])
        recommended_cards = [rec['card'].slug for rec in recommendations]
        for card_slug in must_include:
            if card_slug not in recommended_cards:
                issues.append(f'Expected card "{card_slug}" not recommended')
        
        # Check must-not-include cards
        must_not_include = expected.get('must_not_include_cards', [])
        for card_slug in must_not_include:
            if card_slug in recommended_cards:
                issues.append(f'Card "{card_slug}" should not be recommended but was')
        
        # Check card count optimization
        card_count_opt = expected.get('card_count_optimization')
        if card_count_opt:
            issues.extend(self.validate_card_count_optimization(recommendations, card_count_opt))
        
        # Check zero fee optimization
        zero_fee_opt = expected.get('zero_fee_optimization')
        if zero_fee_opt:
            issues.extend(self.validate_zero_fee_optimization(recommendations, zero_fee_opt))
        
        # Check portfolio optimization
        portfolio_opt = expected.get('portfolio_optimization')
        if portfolio_opt:
            issues.extend(self.validate_portfolio_optimization(recommendations, portfolio_opt))
        
        # Check value breakdown accuracy (always validate)
        breakdown_issues = self.validate_breakdown_accuracy(recommendations)
        issues.extend(breakdown_issues)
        
        if issues:
            self.stdout.write(self.style.ERROR('⚠️  Validation Issues:'))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f'   • {issue}'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ All expectations met'))
    
    def validate_card_count_optimization(self, recommendations, expected):
        """Validate card count optimization logic."""
        issues = []
        
        expected_count = expected.get('expected_actual_count')
        if expected_count is not None:
            actual_count = len(recommendations)
            if actual_count != expected_count:
                issues.append(f'Card count optimization failed: expected {expected_count} cards, got {actual_count}')
        
        max_recs = expected.get('max_recommendations')
        if max_recs is not None:
            actual_count = len(recommendations)
            # For regular optimization, count should be <= max unless zero fee exception
            has_zero_fee_exception = any('$0' in rec.get('reasoning', '') or rec['card'].annual_fee == 0 
                                       for rec in recommendations)
            if actual_count > max_recs and not has_zero_fee_exception:
                issues.append(f'Exceeded max_recommendations ({max_recs}) without zero fee justification: got {actual_count}')
        
        return issues
    
    def validate_zero_fee_optimization(self, recommendations, expected):
        """Validate zero fee card optimization logic."""
        issues = []
        
        if expected.get('all_cards_zero_fee'):
            for rec in recommendations:
                if rec['card'].annual_fee > 0:
                    issues.append(f'Card "{rec["card"].name}" has annual fee ${rec["card"].annual_fee} but should be $0')
        
        if expected.get('no_fee_justifies_multiple'):
            zero_fee_count = sum(1 for rec in recommendations if rec['card'].annual_fee == 0)
            if zero_fee_count < 2:
                issues.append(f'Expected multiple zero fee cards, got {zero_fee_count}')
        
        return issues
    
    def validate_breakdown_accuracy(self, recommendations):
        """Validate that value breakdowns are accurate and don't double-count spending."""
        issues = []

        # Double-counting is about dollars, not names: a capped category
        # legitimately splits across two cards (e.g. 5x Amazon up to the cap,
        # overflow elsewhere), so we sum each category's allocated spend
        # across held cards and flag only totals exceeding the user's actual
        # spending. Credits, info notes and bonus-window shifts (per-apply
        # counterfactuals) don't allocate steady-state spending.
        from collections import defaultdict
        category_spend = defaultdict(float)
        category_cards = defaultdict(list)

        for rec in recommendations:
            card_name = rec['card'].name
            estimated_rewards = float(rec['estimated_rewards'])
            breakdown = rec.get('rewards_breakdown', [])
            signup_bonus = rec.get('signup_bonus_value', 0)
            annual_fee = float(rec['card'].annual_fee)

            # Calculate breakdown total
            breakdown_total = 0.0
            for item in breakdown:
                category_name = item.get('category_name', 'Unknown')
                category_rewards = item.get('category_rewards', 0)

                if category_rewards:
                    breakdown_total += float(category_rewards)

                if (item.get('type', 'reward_category') == 'reward_category'
                        and rec['action'] in ('apply', 'keep')
                        and item.get('annual_spend')):
                    # Strip the "(5.0x)" rate suffix so cap splits at
                    # different rates aggregate into one category.
                    base_name = category_name.rsplit(' (', 1)[0]
                    category_spend[base_name] += float(item['annual_spend'])
                    category_cards[base_name].append(
                        (card_name, float(item['annual_spend'])))

        # A category may legitimately split across cards (rate caps), but
        # the dollars allocated across all held cards can never exceed what
        # the user actually spends in that category.
        expected_annual = getattr(self, 'scenario_category_annual', None)
        if expected_annual is not None:
            for base_name, spend in category_spend.items():
                limit = expected_annual.get(base_name)
                if limit is not None and spend > limit + 1:
                    names = ', '.join(name for name, _ in category_cards[base_name])
                    issues.append(
                        f'Double-counting detected: "{base_name}" allocates '
                        f'${spend:,.0f} across {names} but actual spending '
                        f'is ${limit:,.0f}')
            
            # Calculate expected total: breakdown + signup bonus - annual fee (for apply/keep cards)
            if rec['action'] == 'apply':
                expected_total = breakdown_total + float(signup_bonus)
                annual_fee_waived = rec['card'].metadata and rec['card'].metadata.get('annual_fee_waived_first_year', False)
                if not annual_fee_waived:
                    expected_total -= annual_fee
            else:  # keep or cancel
                expected_total = breakdown_total - annual_fee
            
            # Allow small rounding differences (< $1)
            difference = abs(estimated_rewards - expected_total)
            if difference >= 1.0:
                issues.append(f'Breakdown mismatch for {card_name}: estimated ${estimated_rewards:.0f} vs calculated ${expected_total:.0f} (diff: ${difference:.2f})')
        
        return issues
    
    def validate_portfolio_optimization(self, recommendations, expected):
        """Validate portfolio optimization logic."""
        issues = []
        
        # Check for negative portfolio prevention
        if expected.get('prevents_negative_portfolio'):
            total_fees = sum(float(rec['card'].annual_fee) for rec in recommendations if rec['action'] in ['keep', 'apply'])
            total_rewards = sum(float(rec['estimated_rewards']) for rec in recommendations)
            net_value = total_rewards - total_fees
            
            if net_value < 0:
                issues.append(f'Portfolio has negative net value: ${net_value:.2f} (rewards: ${total_rewards:.2f}, fees: ${total_fees:.2f})')
        
        # Check minimum net portfolio value
        min_net_value = expected.get('net_portfolio_value_min')
        if min_net_value is not None:
            total_fees = sum(float(rec['card'].annual_fee) for rec in recommendations if rec['action'] in ['keep', 'apply'])
            total_rewards = sum(float(rec['estimated_rewards']) for rec in recommendations)
            net_value = total_rewards - total_fees
            
            if net_value < min_net_value:
                issues.append(f'Net portfolio value ${net_value:.2f} below minimum ${min_net_value}')
        
        # Check total annual spending validation
        expected_spending = expected.get('total_annual_spending')
        if expected_spending:
            # Note: This would need to be passed from the recommendation engine
            # For now, just validate that spending data is being considered
            pass
        
        # Check empty portfolio acceptance
        if expected.get('empty_portfolio_acceptable') and len(recommendations) == 0:
            # This is expected and acceptable - no issues
            pass
        elif expected.get('empty_portfolio_acceptable') and len(recommendations) > 0:
            # Verify that the non-empty portfolio is actually better than empty
            total_fees = sum(float(rec['card'].annual_fee) for rec in recommendations if rec['action'] in ['keep', 'apply'])
            total_rewards = sum(float(rec['estimated_rewards']) for rec in recommendations)
            net_value = total_rewards - total_fees
            
            if net_value <= 0:
                issues.append(f'Non-empty portfolio should provide positive value, got ${net_value:.2f}')
        
        # Check rejection of high-fee combinations
        if expected.get('rejects_high_fee_combinations'):
            total_fees = sum(float(rec['card'].annual_fee) for rec in recommendations if rec['action'] in ['keep', 'apply'])
            high_fee_cards = [rec for rec in recommendations if float(rec['card'].annual_fee) > 400]
            
            if len(high_fee_cards) > 1:
                card_names = [rec['card'].name for rec in high_fee_cards]
                issues.append(f'Multiple high-fee cards recommended: {card_names} (combined fees: ${total_fees})')
        
        if expected.get('no_overlapping_categories'):
            # Check that cards don't have overlapping reward categories
            category_coverage = {}
            for rec in recommendations:
                card = rec['card']
                for reward_cat in card.reward_categories.filter(is_active=True):
                    category_slug = reward_cat.category.slug
                    if category_slug in category_coverage:
                        issues.append(f'Overlapping category "{category_slug}" found in cards: {category_coverage[category_slug]} and {card.name}')
                    else:
                        category_coverage[category_slug] = card.name
        
        if expected.get('complementary_coverage'):
            # Ensure recommended cards provide complementary, not redundant coverage
            apply_cards = [rec for rec in recommendations if rec['action'] == 'apply']
            if len(apply_cards) > 1:
                # Check that each card specializes in different categories
                primary_categories = []
                for rec in apply_cards:
                    card = rec['card']
                    best_rate = 0
                    best_category = None
                    for reward_cat in card.reward_categories.filter(is_active=True):
                        if float(reward_cat.reward_rate) > best_rate:
                            best_rate = float(reward_cat.reward_rate)
                            best_category = reward_cat.category.slug
                    if best_category and best_category in primary_categories:
                        issues.append(f'Multiple cards optimized for same category "{best_category}"')
                    elif best_category:
                        primary_categories.append(best_category)
        
        complementary_cats = expected.get('complementary_categories', [])
        if complementary_cats:
            recommended_categories = set()
            for rec in recommendations:
                for reward_cat in rec['card'].reward_categories.filter(is_active=True):
                    recommended_categories.add(reward_cat.category.slug)
            
            for category in complementary_cats:
                if category not in recommended_categories:
                    issues.append(f'Expected complementary category "{category}" not covered by recommendations')
        
        return issues
    
    def setup_test_data(self):
        """Set up references to existing data."""
        # Ensure test setup data exists
        self.create_test_setup_data()
        
        # Get existing reward types
        self.reward_types = {}
        for rt in RewardType.objects.all():
            self.reward_types[rt.name] = rt
        
        # Get existing issuers  
        self.issuers = {}
        for issuer in Issuer.objects.all():
            self.issuers[issuer.name] = issuer
        
        # Get existing spending categories
        self.categories = {}
        category_mapping = {
            'groceries': ['Groceries', 'groceries'],
            'dining': ['Dining & Restaurants', 'Dining', 'dining'],
            'gas': ['Gas Stations', 'Gas', 'gas'],
            'travel': ['Travel', 'travel'],
            'general': ['General', 'Other', 'general', 'other'],
        }
        
        for category in SpendingCategory.objects.all():
            self.categories[category.display_name] = category
            # Also map by name and slug for flexibility
            self.categories[category.name] = category
            if category.slug:
                self.categories[category.slug] = category
    
    def create_test_scenario(self, scenario_data):
        """Create a test scenario from JSON data."""
        # Create user and profile
        username = f"scenario_{scenario_data['name'].lower().replace(' ', '_').replace('-', '_')}"
        
        # Clean up existing test user if it exists
        try:
            existing_user = User.objects.get(username=username)
            existing_user.delete()
        except User.DoesNotExist:
            pass
        
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com"
        )
        
        profile = UserSpendingProfile.objects.create(user=user)
        
        # Create spending amounts. Scenario slugs that don't exist as
        # categories map onto their closest real category; anything still
        # unmatched is a loud error — silently dropping spending makes
        # every downstream number wrong.
        category_aliases = {
            'general': 'other',
        }

        # Remember per-category annual totals (by display name, matching
        # breakdown line items) so validate_breakdown_accuracy can verify
        # allocated spending never exceeds actual spending.
        self.scenario_category_annual = {}
        for category_slug, amount in scenario_data['user_profile']['spending'].items():
            category = (self.categories.get(category_slug)
                        or self.categories.get(category_aliases.get(category_slug)))
            if category is None:
                raise ValueError(
                    f"Scenario spending category '{category_slug}' doesn't match "
                    f"any SpendingCategory (known: {sorted(set(self.categories))})")
            SpendingAmount.objects.create(
                profile=profile,
                category=category,
                monthly_amount=Decimal(str(amount))
            )
            display = category.display_name or category.name
            self.scenario_category_annual[display] = (
                self.scenario_category_annual.get(display, 0) + float(amount) * 12)

        # Credit preferences: which card credits (by slug) the user actually
        # redeems. Without these, high-credit cards look cancel-worthy when
        # they aren't (and vice versa). Unknown slugs are a loud error.
        credit_slugs = scenario_data['user_profile'].get('spending_credit_preferences', [])
        if credit_slugs:
            from cards.models import SpendingCredit, UserSpendingCreditPreference
            for slug in credit_slugs:
                try:
                    credit = SpendingCredit.objects.get(slug=slug)
                except SpendingCredit.DoesNotExist:
                    raise ValueError(
                        f"Scenario credit preference '{slug}' doesn't match any "
                        f"SpendingCredit slug")
                UserSpendingCreditPreference.objects.create(
                    profile=profile,
                    spending_credit=credit,
                    values_credit=True
                )

        # Create available cards. Track which ones we actually CREATE (vs
        # fetched pre-existing) so CLI cleanup can remove them — otherwise
        # every run_scenario invocation leaks fixture cards into the dev DB,
        # and they start showing up in real recommendations.
        created_cards = {}
        self.created_fixture_cards = []
        for card_slug in scenario_data['available_cards']:
            existed = CreditCard.objects.filter(slug=card_slug).exists()
            card = self.create_credit_card_from_slug(card_slug)
            created_cards[card_slug] = card
            if not existed:
                self.created_fixture_cards.append(card)
        
        # Create owned cards. Two forms:
        #   "card-slug"                       -> open card, opened ~6 months ago
        #   {"card": "card-slug",             -> full history entry, for
        #    "opened_days_ago": 90,              eligibility-rule scenarios
        #    "closed_days_ago": 30,              (5/24 windows, Amex lifetime,
        #    "bonus_earned_days_ago": 60}        Citi 48-month...)
        # Days-ago values keep scenarios evergreen (an absolute date would
        # silently drift out of every eligibility window); absolute
        # "opened_date"/"closed_date"/"bonus_earned_date" ISO strings are
        # also accepted. Dict-form cards must exist in available_cards — a
        # typo silently creating no history would make the test vacuous.
        for owned_entry in scenario_data.get('owned_cards', []):
            if isinstance(owned_entry, dict):
                owned_card_slug = owned_entry['card']
                if owned_card_slug not in created_cards:
                    raise ValueError(
                        f"Scenario owned card '{owned_card_slug}' is not in "
                        f"available_cards — history entries must reference "
                        f"cards the scenario defines")

                def parse(key):
                    if owned_entry.get(f'{key}_days_ago') is not None:
                        return date.today() - timedelta(
                            days=int(owned_entry[f'{key}_days_ago']))
                    if owned_entry.get(f'{key}_date'):
                        return date.fromisoformat(owned_entry[f'{key}_date'])
                    return None

                UserCard.objects.create(
                    user=profile.user,
                    card=created_cards[owned_card_slug],
                    opened_date=parse('opened') or (date.today() - timedelta(days=180)),
                    closed_date=parse('closed'),
                    bonus_earned_date=parse('bonus_earned'),
                )
            elif owned_entry in created_cards:
                UserCard.objects.create(
                    user=profile.user,
                    card=created_cards[owned_entry],
                    opened_date=date.today() - timedelta(days=180),
                    # Note: is_active is now a property based on closed_date
                    # Card is active by default since closed_date is None
                )

        return profile, created_cards
    
    def create_credit_card_from_slug(self, card_slug):
        """Get or create a credit card from card slug."""
        # First try to find existing card in database
        try:
            existing_card = CreditCard.objects.get(slug=card_slug)
            return existing_card
        except CreditCard.DoesNotExist:
            pass
        
        # If not found, try to create from test definitions
        # Load card definitions if not already loaded
        if not hasattr(self, 'card_definitions'):
            cards_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                'data', 'tests', 'cards.json'
            )
            if os.path.exists(cards_file):
                with open(cards_file, 'r') as f:
                    self.card_definitions = json.load(f)
            else:
                self.card_definitions = []
        
        # Find card definition by slug
        card_def = None
        for card in self.card_definitions:
            if card['slug'] == card_slug:
                card_def = card
                break
        
        if not card_def:
            raise ValueError(f"Card definition not found: {card_slug} (not in database or test definitions)")
        
        return self.create_credit_card(card_def)

# REMOVED: Deprecated create_credit_card_from_name method
    # Use create_credit_card_from_slug instead
    
    def create_credit_card(self, card_data):
        """Create a credit card from JSON data."""
        card = CreditCard.objects.create(
            name=card_data['name'],
            slug=card_data['slug'],
            issuer=self.issuers[card_data['issuer']],
            annual_fee=Decimal(str(card_data.get('annual_fee', 0))),
            signup_bonus_amount=card_data.get('signup_bonus_amount'),
            signup_bonus_type=self.reward_types[card_data.get('signup_bonus_type', 'Points')],
            primary_reward_type=self.reward_types[card_data.get('primary_reward_type', 'Points')],
            metadata=card_data.get('metadata', {'reward_value_multiplier': 0.01})
        )
        
        # Create reward categories
        for category_data in card_data.get('reward_categories', []):
            RewardCategory.objects.create(
                card=card,
                category=self.categories[category_data['category']],
                reward_rate=Decimal(str(category_data.get('reward_rate', category_data.get('rate', 1.0)))),
                reward_type=self.reward_types[category_data.get('type', 'Points')],
                max_annual_spend=Decimal(str(category_data.get('max_annual_spend') or category_data.get('max_bonus_amount') or category_data.get('max_spend'))) if category_data.get('max_annual_spend') or category_data.get('max_bonus_amount') or category_data.get('max_spend') else None,
                is_active=True
            )
        
        return card
    
    def create_test_setup_data(self):
        """Create test setup data (issuers, reward types, spending categories) if they don't exist."""
        import json
        import os
        
        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        setup_dir = os.path.join(project_root, 'data', 'tests', 'setup')
        
        # Create issuers
        issuers_file = os.path.join(setup_dir, 'issuers.json')
        if os.path.exists(issuers_file):
            with open(issuers_file, 'r') as f:
                issuers_data = json.load(f)
            
            for issuer_data in issuers_data:
                issuer, created = Issuer.objects.get_or_create(
                    name=issuer_data['name'],
                    defaults={
                        'slug': issuer_data.get('slug', issuer_data['name'].lower().replace(' ', '-')),
                        'max_cards_per_period': issuer_data.get('max_cards_per_period', 5),
                        'period_months': issuer_data.get('period_months', 24)
                    }
                )
                if created:
                    self.stdout.write(f'✅ Created issuer: {issuer.name}')
        
        # Create reward types
        reward_types_file = os.path.join(setup_dir, 'reward_types.json')
        if os.path.exists(reward_types_file):
            with open(reward_types_file, 'r') as f:
                reward_types_data = json.load(f)
            
            for rt_data in reward_types_data:
                rt, created = RewardType.objects.get_or_create(
                    name=rt_data['name'],
                    defaults={
                        'slug': rt_data.get('slug', rt_data['name'].lower().replace(' ', '-'))
                    }
                )
                if created:
                    self.stdout.write(f'✅ Created reward type: {rt.name}')
        
        # Create spending categories
        categories_file = os.path.join(setup_dir, 'spending_categories.json')
        if os.path.exists(categories_file):
            with open(categories_file, 'r') as f:
                categories_data = json.load(f)
            
            for cat_data in categories_data:
                cat, created = SpendingCategory.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={
                        'slug': cat_data.get('slug', cat_data['name'].lower().replace(' ', '-')),
                        'display_name': cat_data.get('display_name', cat_data['name']),
                        'description': cat_data.get('description', ''),
                        'icon': cat_data.get('icon', 'fas fa-circle'),
                        'sort_order': cat_data.get('sort_order', 100)
                    }
                )
                if created:
                    self.stdout.write(f'✅ Created spending category: {cat.display_name}')

            # Second pass: wire up parent links (parents may appear later
            # in the file than their children)
            for cat_data in categories_data:
                parent_name = cat_data.get('parent')
                if parent_name:
                    try:
                        parent = SpendingCategory.objects.get(name=parent_name)
                        SpendingCategory.objects.filter(
                            name=cat_data['name'], parent__isnull=True
                        ).update(parent=parent)
                    except SpendingCategory.DoesNotExist:
                        pass
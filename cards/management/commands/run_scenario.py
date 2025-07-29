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
            default='data/tests/scenarios.json',
            help='JSON file containing scenarios (default: data/tests/scenarios.json)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed breakdown information'
        )
    
    def handle(self, *args, **options):
        # Get project root directory (go up from cards/management/commands/ to project root)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        scenarios_file = os.path.join(project_root, options['file'])
        
        if not os.path.exists(scenarios_file):
            raise CommandError(f'Scenarios file not found: {scenarios_file}')
        
        with open(scenarios_file, 'r') as f:
            data = json.load(f)
            scenarios = data.get('scenarios', [])
        
        if not scenarios:
            raise CommandError('No scenarios found in file')
        
        if options['list']:
            self.list_scenarios(scenarios)
            return
        
        # Set up test data
        self.setup_test_data()
        
        if options['all']:
            self.run_all_scenarios(scenarios, options['verbose'])
        elif options['scenario_name']:
            self.run_single_scenario(scenarios, options['scenario_name'], options['verbose'])
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
        
        # Create roadmap
        roadmap = Roadmap.objects.create(
            profile=profile,
            name=f"Scenario: {scenario_data['name']}",
            max_recommendations=scenario_data.get('expected_recommendations', {}).get('count', 5)
        )
        
        # Generate recommendations
        engine = RecommendationEngine(profile)
        recommendations = engine.generate_quick_recommendations(roadmap)
        
        # Display results
        self.display_results(scenario_data, recommendations, verbose)
        
        # Cleanup
        profile.user.delete()  # This will cascade delete everything
    
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
        
        # Show owned cards
        owned_cards = scenario_data.get('owned_cards', [])
        if owned_cards:
            self.stdout.write(f'Currently Owned Cards: {", ".join(owned_cards)}')
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
            self.stdout.write('')
        
        # Validate against expectations if provided
        expected = scenario_data.get('expected_recommendations', {})
        if expected:
            self.validate_expectations(recommendations, expected, scenario_data['name'])
    
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
        recommended_cards = [rec['card'].name for rec in recommendations]
        for card_name in must_include:
            if card_name not in recommended_cards:
                issues.append(f'Expected card "{card_name}" not recommended')
        
        # Check must-not-include cards
        must_not_include = expected.get('must_not_include_cards', [])
        for card_name in must_not_include:
            if card_name in recommended_cards:
                issues.append(f'Card "{card_name}" should not be recommended but was')
        
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
    
    def validate_portfolio_optimization(self, recommendations, expected):
        """Validate portfolio optimization logic."""
        issues = []
        
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
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com"
        )
        
        profile = UserSpendingProfile.objects.create(user=user)
        
        # Create spending amounts
        category_mapping = {
            'groceries': 'Groceries',
            'dining': 'Dining',
            'gas': 'Gas',
            'travel': 'Travel',
            'general': 'General',
        }
        
        for category_slug, amount in scenario_data['user_profile']['spending'].items():
            category_name = category_mapping.get(category_slug, category_slug)
            if category_name in self.categories:
                SpendingAmount.objects.create(
                    profile=profile,
                    category=self.categories[category_name],
                    monthly_amount=Decimal(str(amount))
                )
        
        # Create available cards
        created_cards = {}
        for card_name in scenario_data['available_cards']:
            card = self.create_credit_card_from_name(card_name)
            created_cards[card_name] = card
        
        # Create owned cards
        for owned_card_name in scenario_data.get('owned_cards', []):
            if owned_card_name in created_cards:
                UserCard.objects.create(
                    profile=profile,
                    card=created_cards[owned_card_name],
                    opened_date=date.today() - timedelta(days=180),
                    is_active=True
                )
        
        return profile, created_cards
    
    def create_credit_card_from_name(self, card_name):
        """Create a credit card from card name using centralized definitions."""
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
        
        # Find card definition by name
        card_def = None
        for card in self.card_definitions:
            if card['name'] == card_name:
                card_def = card
                break
        
        if not card_def:
            raise ValueError(f"Card definition not found: {card_name}")
        
        return self.create_credit_card(card_def)
    
    def create_credit_card(self, card_data):
        """Create a credit card from JSON data."""
        card = CreditCard.objects.create(
            name=card_data['name'],
            issuer=self.issuers[card_data['issuer']],
            annual_fee=Decimal(str(card_data.get('annual_fee', 0))),
            signup_bonus_amount=card_data.get('signup_bonus_amount'),
            signup_bonus_type=self.reward_types[card_data.get('signup_bonus_type', 'points')],
            primary_reward_type=self.reward_types[card_data.get('primary_reward_type', 'points')],
            metadata=card_data.get('metadata', {'reward_value_multiplier': 0.01})
        )
        
        # Create reward categories
        for category_data in card_data.get('reward_categories', []):
            RewardCategory.objects.create(
                card=card,
                category=self.categories[category_data['category']],
                reward_rate=Decimal(str(category_data['rate'])),
                reward_type=self.reward_types[category_data.get('type', 'points')],
                max_annual_spend=Decimal(str(category_data['max_spend'])) if category_data.get('max_spend') else None,
                is_active=True
            )
        
        return card
"""
Shared base classes for the data-driven recommendation test suites.

These bases deliberately reuse the scenario plumbing from the
`run_scenario` management command (cards/management/commands/run_scenario.py)
so tests and the CLI exercise the exact same setup and validation code.

Used by:
    cards/test_data_driven.py   -> CreditCardTestBase
    cards/test_json_scenarios.py -> JSONScenarioTestBase
"""

from io import StringIO

from django.core.management.base import OutputWrapper
from django.test import TestCase

from cards.management.commands.run_scenario import Command as ScenarioCommand
from cards.scenario_loader import ScenarioLoader
from roadmaps.models import Roadmap
from roadmaps.recommendation_engine import RecommendationEngine


class CreditCardTestBase(TestCase):
    """Runs a scenario dict through the real recommendation engine.

    Scenario format matches data/tests/scenarios/*.json:
        name, user_profile.spending, owned_cards, available_cards,
        expected_recommendations (count/actions/min_total_value/
        must_include_cards/must_not_include_cards/...)
    """

    def setUp(self):
        super().setUp()
        self.command = ScenarioCommand()
        # Silence the command's stdout during tests; failures surface as
        # assertions instead.
        self.command.stdout = OutputWrapper(StringIO())
        self.command.setup_test_data()

    def run_scenario_test(self, scenario):
        """Create the scenario's data, generate recommendations, assert
        the scenario's expectations, and return the recommendations."""
        profile, _created_cards = self.command.create_test_scenario(scenario)

        expected = scenario.get('expected_recommendations', {})
        roadmap = Roadmap.objects.create(
            profile=profile,
            name=f"Scenario: {scenario['name']}",
            max_recommendations=expected.get('count', 5),
        )

        engine = RecommendationEngine(profile)
        recommendations = engine.generate_quick_recommendations(roadmap)

        self.assert_expectations(scenario, recommendations)
        return recommendations

    def assert_expectations(self, scenario, recommendations):
        """Validate recommendations against the scenario's expectations,
        reusing the management command's validators."""
        expected = scenario.get('expected_recommendations', {})
        if not expected:
            return

        issues = []

        expected_count = expected.get('count')
        if expected_count is not None and len(recommendations) != expected_count:
            issues.append(
                f'Expected {expected_count} recommendations, got {len(recommendations)}'
            )

        actual_actions = [rec['action'] for rec in recommendations]
        for action in expected.get('actions', []):
            if action not in actual_actions:
                issues.append(f'Expected action "{action}" not found')

        min_value = expected.get('min_total_value')
        if min_value is not None:
            total_value = sum(float(rec['estimated_rewards']) for rec in recommendations)
            if total_value < min_value:
                issues.append(
                    f'Total value ${total_value:.2f} below minimum ${min_value}'
                )

        recommended_slugs = [rec['card'].slug for rec in recommendations]
        for card_slug in expected.get('must_include_cards', []):
            if card_slug not in recommended_slugs:
                issues.append(f'Expected card "{card_slug}" not recommended')
        for card_slug in expected.get('must_not_include_cards', []):
            if card_slug in recommended_slugs:
                issues.append(f'Card "{card_slug}" should not be recommended but was')

        if expected.get('card_count_optimization'):
            issues.extend(self.command.validate_card_count_optimization(
                recommendations, expected['card_count_optimization']))
        if expected.get('zero_fee_optimization'):
            issues.extend(self.command.validate_zero_fee_optimization(
                recommendations, expected['zero_fee_optimization']))
        if expected.get('portfolio_optimization'):
            issues.extend(self.command.validate_portfolio_optimization(
                recommendations, expected['portfolio_optimization']))
        issues.extend(self.command.validate_breakdown_accuracy(recommendations))

        if issues:
            self.fail(
                f"Scenario '{scenario['name']}' failed expectations:\n  - "
                + "\n  - ".join(issues)
            )

    def print_scenario_results(self, scenario, recommendations):
        """Print scenario results in a readable format (visible with -v 2
        or when a test fails under --buffer)."""
        print(f"\n{'=' * 50}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'=' * 50}")

        if not recommendations:
            print("No recommendations generated.")
            return

        total_value = sum(float(rec['estimated_rewards']) for rec in recommendations)
        print(f"Total Estimated Value: ${total_value:.2f}")
        print(f"Number of Recommendations: {len(recommendations)}")

        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['action'].upper()}: {rec['card'].name}")
            print(f"   Annual Fee: ${rec['card'].annual_fee}")
            print(f"   Estimated Annual Value: ${rec['estimated_rewards']}")
            print(f"   Reasoning: {rec['reasoning']}")
            for breakdown in rec.get('rewards_breakdown') or []:
                print(f"     • {breakdown['category_name']}: {breakdown['calculation']}")

        print(f"\n{'=' * 50}")


class JSONScenarioTestBase(CreditCardTestBase):
    """Loads the JSON scenario suite from data/tests/scenarios/ into
    self.scenarios (ordered: files sorted by name, scenarios in file order)."""

    def setUp(self):
        super().setUp()
        try:
            data = ScenarioLoader.load_scenarios()
        except FileNotFoundError:
            self.scenarios = []
        else:
            self.scenarios = data.get('scenarios', [])

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

        # Mirrors run_scenario.run_scenario: a strategy preset supplies the
        # card-pool filters and the new-application cap.
        from roadmaps.strategies import resolve_scenario_strategy, apply_strategy_to_roadmap
        strategy = resolve_scenario_strategy(scenario)

        expected = scenario.get('expected_recommendations', {})
        # Top-level max_recommendations beats the strategy preset and the
        # count-derived default (mirrors run_scenario) — bonus-capacity
        # scenarios must allow more applies than they expect to survive.
        if 'max_recommendations' in scenario:
            max_recommendations = scenario['max_recommendations']
        elif strategy:
            max_recommendations = strategy['max_recommendations']
        else:
            max_recommendations = expected.get('count', 5)
        roadmap = Roadmap.objects.create(
            profile=profile,
            name=f"Scenario: {scenario['name']}",
            max_recommendations=max_recommendations,
        )
        apply_strategy_to_roadmap(roadmap, strategy)

        engine = RecommendationEngine(profile, strategy=strategy)
        recommendations = engine.generate_quick_recommendations(roadmap)

        # DUMP_SCENARIOS=1 prints every scenario's full results BEFORE the
        # assertions — the recalibration workflow needs the actual numbers
        # from the clean test DB (the CLI runs against the dev DB, whose
        # real cards pollute scenario pools).
        import os
        if os.environ.get('DUMP_SCENARIOS'):
            self.print_scenario_results(scenario, recommendations)

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
        # Phase E: expected_apply_sequence / expected_recommended_months
        # (no-ops for scenarios that don't set them)
        issues.extend(self.command.validate_apply_sequencing(recommendations, expected))

        # Phase K4: apply_as attribution ({slug: entity_name}) + the
        # single-entity no-op guarantee (see run_scenario.py's
        # validate_expectations — same check, mirrored here since the CLI
        # and test paths validate independently). Keyed on APPLY recs only —
        # a second-copy apply (K2c) can share a slug with a 'keep' rec for
        # the same card, and that keep rec never carries apply_as.
        apply_recs_by_slug = {
            rec['card'].slug: rec for rec in recommendations if rec['action'] == 'apply'}
        for card_slug, entity_name in (expected.get('apply_as') or {}).items():
            rec = apply_recs_by_slug.get(card_slug)
            if rec is None:
                issues.append(
                    f'Expected apply_as for "{card_slug}" but no recommendation '
                    f'for that card exists')
                continue
            actual_name = (rec.get('apply_as') or {}).get('name')
            if actual_name != entity_name:
                issues.append(
                    f'Expected "{card_slug}" apply_as name "{entity_name}", '
                    f'got "{actual_name}"')
        if 'entities' not in scenario:
            for rec in recommendations:
                if 'apply_as' in rec:
                    issues.append(
                        f'Single-entity scenario unexpectedly carries apply_as '
                        f'on "{rec["card"].slug}"')

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
            if rec['action'] == 'apply':
                print(f"   Recommended month: {rec.get('recommended_month')}"
                     f" (bonus needs {rec.get('bonus_months_needed')} months;"
                     f" bonus_deferred={rec.get('bonus_deferred')})")
            for breakdown in rec.get('rewards_breakdown') or []:
                print(f"     • {breakdown['category_name']}: {breakdown['calculation']}")

        bonus_capacity = recommendations[0].get('portfolio_summary', {}).get('bonus_capacity')
        if bonus_capacity:
            print(f"\nBonus capacity: {bonus_capacity['months_committed']}/"
                 f"{bonus_capacity['capacity_months']} months committed")
            for entry in bonus_capacity.get('timeline') or []:
                print(f"   {entry['card_name']}: month {entry['recommended_month']}"
                     f" (needs {entry['months_needed']} mo, counted={entry['bonus_counted']})")
            if bonus_capacity.get('deferred_applies'):
                print(f"   Deferred (assembly safety net): {bonus_capacity['deferred_applies']}")
            if bonus_capacity.get('bonus_less_applies'):
                print(f"   Bonus-less (fits selection, not this year's budget): "
                     f"{bonus_capacity['bonus_less_applies']}")

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

    def get_scenario(self, name):
        """Find a scenario by name (file order is not a stable address)."""
        for scenario in self.scenarios:
            if scenario.get('name') == name:
                return scenario
        self.fail(f"Scenario '{name}' not found in data/tests/scenarios/")

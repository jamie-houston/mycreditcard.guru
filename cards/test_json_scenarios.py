"""
JSON-based data-driven test suite for credit card recommendations.

This test suite loads scenarios from JSON files, making it easy to add
new test cases without modifying Python code.

Usage:
    python manage.py test cards.test_json_scenarios
    
To add new scenarios:
    1. Edit files in data/input/tests/scenarios/
    2. Add your scenario to the appropriate category file
    3. Run the tests
"""

import os
import json
from django.test import TestCase
from .test_base import JSONScenarioTestBase


class JSONScenarioTest(JSONScenarioTestBase):
    """Test cases that load scenarios from JSON files."""
    
    def test_young_professional_dining_focus(self):
        """Test the Young Professional - Dining Focus scenario."""
        if not self.scenarios:
            self.skipTest("No scenarios found in JSON file")
        scenario = self.scenarios[0]  # Young Professional - Dining Focus
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_business_traveler(self):
        """Test the Business Traveler scenario."""
        if not self.scenarios:
            self.skipTest("No scenarios found in JSON file")
        scenario = self.scenarios[1]  # Business Traveler
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_family_high_grocery_spend(self):
        """Test the Family with High Grocery Spend scenario."""
        if not self.scenarios:
            self.skipTest("No scenarios found in JSON file")
        scenario = self.scenarios[2]  # Family with High Grocery Spend
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_existing_high_fee_card_review(self):
        """Test the Existing High-Fee Card Review scenario."""
        if not self.scenarios:
            self.skipTest("No scenarios found in JSON file")
        scenario = self.scenarios[20]  # Existing High-Fee Card Review
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_multiple_cards_optimization(self):
        """Test the Multiple Cards Optimization scenario."""
        if not self.scenarios:
            self.skipTest("No scenarios found in JSON file")
        scenario = self.scenarios[4]  # Multiple Cards Optimization
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        


class ScenarioValidationTest(TestCase):
    """Test the JSON scenario validation and loading."""
    
    def test_json_file_exists(self):
        """Test that the JSON scenarios directory exists."""
        scenarios_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'tests', 'scenarios'
        )
        self.assertTrue(
            os.path.exists(scenarios_dir),
            f"Scenarios directory not found at {scenarios_dir}"
        )
        
        # Also check for the index file
        index_file = os.path.join(scenarios_dir, 'index.json')
        self.assertTrue(
            os.path.exists(index_file),
            f"Scenarios index file not found at {index_file}"
        )
    
    def test_json_file_valid(self):
        """Test that the scenario files are valid JSON and can be loaded."""
        from .scenario_loader import ScenarioLoader
        
        try:
            data = ScenarioLoader.load_scenarios()
            self.assertIsInstance(data, dict)
            self.assertIn('scenarios', data)
            self.assertIsInstance(data['scenarios'], list)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.fail(f"Failed to load or parse scenario files: {e}")
    
    def test_scenario_structure(self):
        """Test that each scenario has the required structure."""
        from .scenario_loader import ScenarioLoader
        
        try:
            data = ScenarioLoader.load_scenarios()
        except FileNotFoundError:
            self.skipTest("Scenario files not found")
            
        required_fields = ['name', 'user_profile', 'available_cards']
        
        for i, scenario in enumerate(data.get('scenarios', [])):
            for field in required_fields:
                self.assertIn(
                    field, 
                    scenario, 
                    f"Scenario {i} missing required field '{field}'"
                )
            
            # Validate user_profile structure
            self.assertIn(
                'spending', 
                scenario['user_profile'],
                f"Scenario {i} user_profile missing 'spending'"
            )
            
            # Validate available_cards structure
            self.assertIsInstance(
                scenario['available_cards'],
                list,
                f"Scenario {i} available_cards should be a list"
            )
            
            # Cards can be either strings (card names) or objects
            for j, card in enumerate(scenario['available_cards']):
                if isinstance(card, str):
                    # Card name string - just validate it's not empty
                    self.assertTrue(
                        len(card.strip()) > 0,
                        f"Scenario {i} card {j} name should not be empty"
                    )
                elif isinstance(card, dict):
                    # Card object - validate required fields
                    card_required_fields = ['name', 'issuer', 'primary_reward_type']
                    for field in card_required_fields:
                        self.assertIn(
                            field,
                            card,
                            f"Scenario {i} card {j} missing required field '{field}'"
                        )
                else:
                    self.fail(f"Scenario {i} card {j} should be string or dict, got {type(card)}")


def print_scenario_results(scenario_name, recommendations):
    """Utility function to print scenario results in a readable format."""
    print(f"\n{'='*50}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*50}")
    
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
        print(f"   Priority: {rec.get('priority', 'N/A')}")
        print(f"   Reasoning: {rec['reasoning']}")
        
        if rec.get('rewards_breakdown'):
            print("   Detailed Breakdown:")
            for breakdown in rec['rewards_breakdown']:
                print(f"     • {breakdown['category_name']}: {breakdown['calculation']}")
    
    print(f"\n{'='*50}")
    print(f"\n{'='*50}")
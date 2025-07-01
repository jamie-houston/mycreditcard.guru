"""
Data-driven test suite for credit card recommendations.

This test suite uses centralized card definitions and provides
predefined scenarios for testing the recommendation engine.

Usage:
    python manage.py test cards.test_data_driven
"""

from .test_base import CreditCardTestBase


class DataDrivenRecommendationTest(CreditCardTestBase):
    """
    Base class for data-driven recommendation tests using centralized card definitions.
    """


class CreditCardRecommendationScenarios(DataDrivenRecommendationTest):
    """
    Specific test scenarios for credit card recommendations using centralized card definitions.
    """
    
    SCENARIOS = [
        {
            'name': 'High Grocery Spender',
            'user_profile': {
                'spending': {
                    'groceries': 1000,
                    'dining': 200,
                    'gas': 150,
                    'general': 500
                }
            },
            'owned_cards': [],
            'available_cards': ['Blue Cash Preferred® Card', 'Freedom Unlimited'],
            'expected_recommendations': {
                'actions': ['apply'],
                'min_total_value': 400,
                'must_include_cards': ['Blue Cash Preferred® Card']
            }
        },
        {
            'name': 'Travel Enthusiast',
            'user_profile': {
                'spending': {
                    'travel': 800,
                    'dining': 400,
                    'groceries': 300,
                    'general': 700
                }
            },
            'owned_cards': [],
            'available_cards': ['Chase Sapphire Preferred® Card', 'Venture Rewards Credit Card'],
            'expected_recommendations': {
                'actions': ['apply'],
                'min_total_value': 600,
                'must_include_cards': ['Chase Sapphire Preferred® Card']
            }
        },
        {
            'name': 'Existing Card Optimization',
            'user_profile': {
                'spending': {
                    'groceries': 200,
                    'dining': 150,
                    'gas': 100,
                    'general': 300
                }
            },
            'owned_cards': ['Low Value Card'],
            'available_cards': ['Low Value Card', 'Better Card'],
            'expected_recommendations': {
                'actions': ['cancel', 'apply'],
                'min_total_value': 50,
                'must_include_cards': ['Better Card']
            }
        }
    ]
    
    def test_high_grocery_spender(self):
        """Test the High Grocery Spender scenario."""
        scenario = self.SCENARIOS[0]  # High Grocery Spender
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_travel_enthusiast(self):
        """Test the Travel Enthusiast scenario."""
        scenario = self.SCENARIOS[1]  # Travel Enthusiast
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        
    def test_existing_card_optimization(self):
        """Test the Existing Card Optimization scenario."""
        scenario = self.SCENARIOS[2]  # Existing Card Optimization
        recommendations = self.run_scenario_test(scenario)
        self.print_scenario_results(scenario, recommendations)
        


class CustomScenarioRunner:
    """
    Utility class for running custom scenarios outside of Django's test framework.
    
    Usage:
        runner = CustomScenarioRunner()
        runner.setup_database()
        results = runner.run_scenario(scenario_data)
    """
    
    def __init__(self):
        self.test_case = None
        
    def setup_database(self):
        """Set up the database with test data."""
        # Note: This should be called within a transaction or test case
        # For actual usage, you'd want to use Django's test utilities
        pass
        
    def run_scenario(self, scenario_data):
        """Run a single scenario and return results."""
        # This would be implemented to work outside of Django's test framework
        # For now, use the test case approach above
        pass


# Example of how to add a new scenario:
EXAMPLE_NEW_SCENARIO = {
    'name': 'Gas Station Heavy User',
    'user_profile': {
        'spending': {
            'gas': 500,
            'groceries': 300,
            'dining': 200,
            'general': 400
        }
    },
    'owned_cards': [],
    'available_cards': [
        {
            'name': 'Gas Rewards Card',
            'issuer': 'chase',
            'annual_fee': 0,
            'signup_bonus_amount': 20000,
            'signup_bonus_type': 'points',
            'primary_reward_type': 'points',
            'metadata': {'reward_value_multiplier': 0.01},
            'reward_categories': [
                {'category': 'gas', 'rate': 5.0, 'type': 'points', 'max_spend': 12000},
                {'category': 'general', 'rate': 1.0, 'type': 'points'}
            ]
        }
    ],
    'expected_recommendations': {
        'count': 1,
        'actions': ['apply'],
        'min_total_value': 300,
        'must_include_cards': ['Gas Rewards Card']
    }
}

# To add the new scenario, append it to CreditCardRecommendationScenarios.SCENARIOS
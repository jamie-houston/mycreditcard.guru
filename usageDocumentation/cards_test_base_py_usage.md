# test_base.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `test_base.py` module, which contains comprehensive base test classes for data-driven credit card recommendation testing. The CreditCardTestBase class provides centralized functionality for loading test cards and scenarios, ensuring consistency across all test files with robust scenario validation, card creation utilities, and recommendation verification frameworks.

## Module Overview
`test_base.py` is a 421-line testing infrastructure module that provides base test classes for the credit card recommendation system. It includes the CreditCardTestBase and JSONScenarioTestBase classes that handle test data setup, scenario creation, recommendation testing, and comprehensive validation of recommendation accuracy and breakdown calculations.

### Key Responsibilities:
- **Test Data Management**: Loads card definitions from JSON files and provides methods to create consistent test scenarios with realistic user profiles and card availability
- **Scenario Creation & Validation**: Creates complete test scenarios from scenario data including user profiles, owned cards, available cards, and expected recommendation results with comprehensive validation
- **Recommendation Testing Framework**: Runs scenario tests through the recommendation engine and validates results against expected outcomes with detailed breakdown accuracy checking to prevent double-counting and calculation errors


## Initialization
The test base classes are designed to be inherited by actual test cases. They automatically set up test data and load card definitions.

```python
from cards.test_base import CreditCardTestBase, JSONScenarioTestBase

class MyRecommendationTest(CreditCardTestBase):
    """Test class inheriting from CreditCardTestBase"""
    
    def test_my_scenario(self):
        # Test data is automatically loaded
        # self.issuers, self.reward_types, self.categories available
        scenario_data = {
            'name': 'High Spender Test',
            'user_profile': {'spending': {'groceries': 1000}},
            'available_cards': ['premium-grocery-card'],
            'expected_recommendations': {'actions': ['apply']}
        }
        recommendations = self.run_scenario_test(scenario_data)
        self.print_scenario_results(scenario_data, recommendations)
```

## Public API documentation

### `CreditCardTestBase` Class Methods

#### `load_card_definitions()`
Class method that loads card definitions from data/tests/cards.json.
- **Purpose**: Provides centralized card definition loading for all test scenarios

#### `create_test_scenario(scenario_data)`
Creates a complete test scenario from scenario data dictionary.
- **Parameters**: `scenario_data` - Dict with name, user_profile, owned_cards, available_cards, expected_recommendations
- **Returns**: Tuple of (profile, created_cards) for use in tests
- **Purpose**: Sets up user profiles, spending amounts, and card ownership for testing

#### `run_scenario_test(scenario_data)`
Runs a complete scenario test including setup, recommendation generation, and validation.
- **Parameters**: `scenario_data` - Complete scenario definition
- **Returns**: List of recommendation dictionaries
- **Purpose**: Main method for executing scenario-based tests with validation

#### `validate_recommendations(actual, expected, scenario_name)`
Validates actual recommendations against expected results with comprehensive checks.
- **Parameters**: `actual` - Generated recommendations, `expected` - Expected results, `scenario_name` - Test identifier
- **Purpose**: Ensures recommendation quality, accuracy, and prevents calculation errors

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: Creating Custom Test Scenarios
Build and run custom recommendation test scenarios with validation.

```python
class CustomRecommendationTest(CreditCardTestBase):
    def test_high_dining_spender(self):
        scenario = {
            'name': 'High Dining Spender',
            'user_profile': {
                'spending': {
                    'dining': 1500,  # $1500/month dining
                    'groceries': 300,
                    'general': 500
                }
            },
            'owned_cards': [],
            'available_cards': ['dining-rewards-card', 'general-card'],
            'expected_recommendations': {
                'actions': ['apply'],
                'min_total_value': 400,
                'must_include_cards': ['dining-rewards-card']
            }
        }
        recommendations = self.run_scenario_test(scenario)
        # Automatic validation against expected results
```

### Example 2: Breakdown Validation Testing
Ensure recommendation calculations are accurate and don't double-count spending.

```python
class BreakdownValidationTest(CreditCardTestBase):
    def test_portfolio_optimization_accuracy(self):
        scenario = {
            'name': 'Multi-Card Portfolio',
            'user_profile': {
                'spending': {
                    'groceries': 800,
                    'gas': 400,
                    'dining': 600,
                    'travel': 200
                }
            },
            'owned_cards': ['basic-card'],
            'available_cards': ['grocery-card', 'gas-card', 'dining-card'],
            'expected_recommendations': {'count': 3}
        }
        recommendations = self.run_scenario_test(scenario)
        # validate_breakdown_accuracy automatically called
        # Prevents double-counting across categories
```


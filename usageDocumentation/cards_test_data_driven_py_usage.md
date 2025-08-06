# test_data_driven.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/test_data_driven.py` module, which provides a data-driven test suite for credit card recommendations. The module contains predefined test scenarios and utility classes for running custom scenarios outside Django's test framework, ensuring comprehensive testing of the recommendation engine with realistic user profiles.

## Module Overview
`cards/test_data_driven.py` is a 163-line data-driven testing module that provides centralized test scenarios and custom scenario runners for the recommendation engine. It includes predefined scenarios for common user profiles and example configurations for adding new test cases.

### Key Responsibilities:
- **Predefined Test Scenarios**: Contains SCENARIOS list with realistic user profiles like High Grocery Spender, Travel Enthusiast, and Existing Card Optimization with expected recommendation outcomes
- **Data-Driven Test Classes**: Implements DataDrivenRecommendationTest and CreditCardRecommendationScenarios classes that inherit from CreditCardTestBase for consistent testing
- **Custom Scenario Utilities**: Provides CustomScenarioRunner class for running scenarios outside Django's test framework and example scenario configurations for easy test expansion

## Initialization
Django test classes are automatically discovered and run by Django's test runner. No manual initialization required.

```python
# Run tests via Django management command:
# python manage.py test cards.test_data_driven
# python manage.py test cards.test_data_driven.DataDrivenRecommendationTest
```

## Public API documentation

### Test Classes
- **`DataDrivenRecommendationTest`**: Runs predefined scenarios through the recommendation engine with centralized test data
- **`CreditCardRecommendationScenarios`**: Contains SCENARIOS list with realistic user profiles and expected outcomes
- **`CustomScenarioRunner`**: Utility class for running scenarios outside Django's test framework

### Predefined Test Scenarios
Contains SCENARIOS list with common user profiles:
- High Grocery Spender with cash back preferences
- Travel Enthusiast with premium card tolerance
- Existing Card Optimization scenarios
- Various spending patterns and reward preferences

### Custom Scenario Utilities
- `CustomScenarioRunner` for running scenarios independently
- Example scenario configurations for easy test expansion
- Centralized card definitions and consistent testing patterns

## Dependencies
### External Dependencies:
- `django.test.TestCase`: Django testing framework
- `decimal.Decimal`: Financial precision for calculations

### Internal Dependencies:
- `cards.test_base.CreditCardTestBase`: Base class for credit card testing
- `cards.models`: Credit card models for recommendation testing
- `roadmaps.recommendation_engine`: Core recommendation logic being tested
- Used by: Automated testing, regression testing, recommendation validation

## Practical Code Examples

### Example 1: Running Data-Driven Tests
How to execute predefined scenario tests.

```python
# Run all data-driven scenario tests
# python manage.py test cards.test_data_driven

# Run specific test class
# python manage.py test cards.test_data_driven.DataDrivenRecommendationTest

# Run with detailed output to see scenario results
# python manage.py test cards.test_data_driven --verbosity=2

# Run custom scenario runner outside Django tests
from cards.test_data_driven import CustomScenarioRunner

runner = CustomScenarioRunner()
results = runner.run_scenario({
    "name": "Custom Test",
    "spending": [{"category": "Groceries", "amount": "600.00"}],
    "preferences": {"max_annual_fee": "100.00"}
})
```

### Example 2: Adding New Test Scenarios
How to add new scenarios to the predefined list.

```python
# Example scenario structure in SCENARIOS list:
SCENARIOS = [
    {
        "name": "High Grocery Spender",
        "description": "User who spends $800/month on groceries, prefers cash back",
        "user_profile": {
            "spending": [
                {"category": "Groceries", "amount": "800.00"},
                {"category": "Gas", "amount": "200.00"},
                {"category": "General", "amount": "300.00"}
            ],
            "preferences": {
                "max_annual_fee": "50.00",
                "preferred_reward_type": "Cash Back",
                "preferred_issuer": None
            }
        },
        "expected_results": {
            "min_recommendations": 2,
            "top_card_should_be": "grocery-focused",
            "reward_rate_groceries": ">=3.0"
        }
    },
    # Add new scenarios here following the same structure
    {
        "name": "Your New Scenario",
        "description": "Description of the test case",
        "user_profile": {
            # User spending and preferences
        },
        "expected_results": {
            # Expected recommendation outcomes
        }
    }
]
```

# test_json_scenarios.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/test_json_scenarios.py` module, which provides a JSON-based data-driven test suite for credit card recommendations. The module loads scenarios from JSON files and includes comprehensive validation testing for scenario structure, making it easy to add new test cases without modifying Python code.

## Module Overview
`cards/test_json_scenarios.py` is a 181-line JSON-based testing module that provides external scenario loading and validation for the recommendation engine. It includes test classes for running JSON-loaded scenarios and comprehensive validation of JSON scenario structure and content.

### Key Responsibilities:
- **JSON Scenario Loading**: Implements JSONScenarioTest class that loads scenarios from external JSON files and runs them through the recommendation engine with automatic validation
- **Scenario Structure Validation**: Provides ScenarioValidationTest class that validates JSON file existence, parsing, and scenario structure to ensure data integrity
- **External Test Data Management**: Supports loading scenarios from data/tests/scenarios/ directory with flexible file organization and automatic metadata extraction

## Initialization
Django test classes are automatically discovered and run by Django's test runner. No manual initialization required.

```python
# Run tests via Django management command:
# python manage.py test cards.test_json_scenarios
# python manage.py test cards.test_json_scenarios.JSONScenarioTest
```

## Public API documentation

### Test Classes
- **`JSONScenarioTest`**: Loads scenarios from JSON files and runs them through the recommendation engine with automatic validation
- **`ScenarioValidationTest`**: Validates JSON file existence, parsing, and scenario structure to ensure data integrity

### JSON Scenario Structure
Tests expect JSON files in `data/tests/scenarios/` directory with specific structure:
- Scenario metadata (name, description, expected outcomes)
- User spending profiles and preferences
- Expected recommendation results for validation

### Automated Testing Features
- Loads scenarios from external JSON files without modifying Python code
- Validates scenario structure and content before running tests
- Supports flexible file organization and automatic metadata extraction
- Provides comprehensive error reporting for JSON parsing issues

## Dependencies
### External Dependencies:
- `django.test.TestCase`: Django testing framework
- `json`: JSON file parsing
- `pathlib.Path`: File system operations

### Internal Dependencies:
- `cards.test_base.JSONScenarioTestBase`: Base class for JSON scenario testing
- `cards.scenario_loader`: Utility for loading test scenarios from JSON files
- `cards.models`: Credit card models for testing recommendations
- Used by: Test automation, continuous integration, scenario validation

## Practical Code Examples

### Example 1: Running JSON Scenario Tests
How to execute JSON-based scenario tests.

```python
# Run all JSON scenario tests
# python manage.py test cards.test_json_scenarios

# Run specific test class
# python manage.py test cards.test_json_scenarios.JSONScenarioTest

# Run with verbose output to see scenario details
# python manage.py test cards.test_json_scenarios --verbosity=2

# Run scenario validation tests only
# python manage.py test cards.test_json_scenarios.ScenarioValidationTest
```

### Example 2: JSON Scenario File Structure
Example of how JSON scenario files should be structured.

```python
# File: data/tests/scenarios/travel_enthusiast.json
{
    "scenarios": [
        {
            "name": "High Travel Spender",
            "description": "User who spends heavily on travel and dining",
            "user_profile": {
                "spending": [
                    {"category": "Travel", "amount": "1200.00"},
                    {"category": "Dining", "amount": "800.00"},
                    {"category": "General", "amount": "500.00"}
                ],
                "preferences": {
                    "max_annual_fee": "200.00",
                    "preferred_reward_type": "Travel Points"
                }
            },
            "expected_results": {
                "min_recommendations": 3,
                "top_card_should_contain": "Sapphire",
                "min_total_value": "400.00"
            }
        }
    ]
}

# Test automatically loads this file and validates:
# 1. Scenario structure is correct
# 2. Recommendations meet expected criteria
# 3. Calculation accuracy and reasoning
```

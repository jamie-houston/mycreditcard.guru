# run_scenario.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/management/commands/run_scenario.py` module, which contains a Django management command for running credit card recommendation test scenarios. This command allows testing the recommendation engine with predefined scenarios, validating recommendation accuracy, and generating detailed reports for quality assurance and development testing.

## Module Overview
`cards/management/commands/run_scenario.py` is a Django management command module that implements the `run_scenario` command for executing recommendation test scenarios. It provides command-line testing capabilities for the recommendation engine with comprehensive validation and reporting.

### Key Responsibilities:
- **Scenario Execution**: Runs predefined or custom recommendation test scenarios through the recommendation engine with realistic user profiles and card data
- **Recommendation Validation**: Validates recommendation results against expected outcomes, checks calculation accuracy, and ensures recommendation quality standards
- **Test Reporting**: Generates detailed test reports, recommendation breakdowns, and validation results for quality assurance and development debugging

## Initialization
Django management commands are automatically discovered and executed via Django's management framework. No manual initialization required.

```python
# Execute via Django management command:
# python manage.py run_scenario --file data/tests/scenarios/travel_enthusiast.json
# python manage.py run_scenario --name "High Grocery Spender"
```

## Public API documentation

### Command Class
- **`Command`**: Django management command that inherits from `BaseCommand` for running credit card recommendation test scenarios

### Command Arguments
- **`--file <path>`**: Run scenarios from a specific JSON file
- **`--name <scenario_name>`**: Run a specific named scenario
- **`--all`**: Run all available scenarios in the test directory
- **`--output <path>`**: Save detailed results to a file
- **`--validate-only`**: Validate scenario structure without running recommendations
- **`--verbose`**: Show detailed recommendation analysis and scoring

### Scenario Testing Features
- Executes predefined or custom recommendation test scenarios
- Validates recommendation results against expected outcomes
- Generates detailed reports with recommendation breakdowns
- Supports both individual scenario testing and batch execution
- Quality assurance validation for recommendation engine accuracy

## Dependencies
### External Dependencies:
- `django.core.management.base.BaseCommand`: Django management command framework
- `json`: JSON file parsing for scenario data
- `pathlib.Path`: File system operations for scenario discovery

### Internal Dependencies:
- `roadmaps.recommendation_engine.RecommendationEngine`: Core recommendation logic
- `cards.scenario_loader`: Utility for loading test scenarios
- `cards.models`: Credit card models for scenario data
- Used by: Testing automation, quality assurance, development debugging

## Practical Code Examples

### Example 1: Running Recommendation Scenarios
How to execute recommendation test scenarios via command line.

```python
# Run a specific scenario file
# python manage.py run_scenario --file data/tests/scenarios/travel_enthusiast.json

# Run a named scenario from any file
# python manage.py run_scenario --name "High Travel Spender"

# Run all scenarios with detailed output
# python manage.py run_scenario --all --verbose

# Validate scenario structure without running
# python manage.py run_scenario --file basic_profiles.json --validate-only

# Save results to file for analysis
# python manage.py run_scenario --all --output scenario_results.json
```

### Example 2: Scenario Results and Validation
Example output and validation from running scenarios.

```python
# Command output example:
# Running scenario: "High Travel Spender"
# User Profile:
#   - Travel: $1,200/month
#   - Dining: $800/month  
#   - General: $500/month
# Preferences:
#   - Max Annual Fee: $200
#   - Preferred Reward Type: Travel Points
# 
# Recommendations Generated:
# 1. Chase Sapphire Preferred (Score: 87.5)
#    - Annual Fee: $95
#    - Travel: 2x points ($288/year value)
#    - Dining: 2x points ($192/year value)
#    - Total Annual Value: $480
#    - Reasoning: Strong travel/dining rewards, good transfer partners
#
# 2. Chase Sapphire Reserve (Score: 84.2)
#    - Annual Fee: $550 (effective $250 with credits)
#    - Travel: 3x points ($432/year value)
#    - Dining: 3x points ($288/year value)
#    - Total Annual Value: $720
#    - Reasoning: Premium benefits, higher earning rates
#
# Validation Results:
# ✅ Min recommendations met: 3 generated (expected ≥2)
# ✅ Top card contains "Sapphire" (expected)
# ✅ Min total value: $480 (expected ≥$400)
# ✅ All calculations verified
#
# Scenario: PASSED
```

# analyze_scenarios.py Usage Documentation

## Executive Summary
The `analyze_scenarios.py` module is a test scenario categorization and analysis tool that loads credit card test scenarios and automatically organizes them into thematic categories for analysis purposes. It provides detailed breakdowns of scenario distribution across different test categories and generates comprehensive reports showing how test cases are organized by functionality and user profile types.

## Module Overview
`analyze_scenarios.py` is a command-line analysis script that processes test scenario JSON files to categorize and analyze the distribution of test cases across different functional areas. It serves as a quality assurance tool for understanding test coverage and scenario organization.

### Key Responsibilities:
- **Scenario Loading & Parsing**: Reads test scenarios from JSON files and validates their structure for analysis
- **Pattern-Based Categorization**: Uses name pattern matching to automatically classify scenarios into 7 predefined categories (basic profiles, portfolio optimization, etc.)
- **Distribution Analysis & Reporting**: Generates detailed reports showing scenario counts, categories, and provides insights into test coverage patterns

## Initialization
The script operates on a hardcoded input file (`data/tests/scenarios.json`) and outputs analysis to the console. Designed for scenario analysis and test coverage evaluation.

```python
# Run from command line (primary usage)
python analyze_scenarios.py

# Or import and use programmatically
from analyze_scenarios import load_scenarios, categorize_scenarios, print_analysis
scenarios = load_scenarios()
categories = categorize_scenarios(scenarios)
print_analysis(categories)
```

## Public API documentation

### `load_scenarios()`
Loads test scenario data from the predefined JSON file location.
- **Parameters**: None (hardcoded to `data/tests/scenarios.json`)
- **Returns**: Dict containing the full scenarios JSON structure
- **Purpose**: Provides the raw scenario data for analysis and categorization

### `categorize_scenarios(scenarios_data)`
Analyzes scenario names and categorizes them into 7 predefined functional categories.
- **Parameters**: `scenarios_data` (dict) - The loaded scenarios JSON structure
- **Returns**: Dict with category keys containing scenarios lists and metadata
- **Categories**: basic_profiles, portfolio_optimization, zero_fee_cards, spending_credits, card_count_optimization, edge_cases, signup_bonus
- **Logic**: Uses pattern matching on scenario names for automatic classification

### `print_analysis(categories)`
Generates and displays a comprehensive analysis report of scenario categorization.
- **Parameters**: `categories` (dict) - Categorized scenarios from categorize_scenarios()
- **Returns**: None (prints to console)
- **Output**: Formatted report showing total counts, category breakdowns, and individual scenario listings

## Dependencies

### External Dependencies
- **json**: JSON file reading and data parsing
- **re**: Regular expression operations for pattern matching
- **collections.defaultdict**: Efficient data structure for scenario grouping

### Internal Dependencies
- **File Structure**: Requires `data/tests/scenarios.json` source file
- **No Django Dependencies**: Pure Python script, independent of Django framework

## Practical Code Examples

### Example 1: Complete Scenario Analysis (Primary Use Case)
Use this to analyze the distribution and organization of test scenarios across different functional categories.

```python
# Run complete analysis from command line
python analyze_scenarios.py

# Expected output:
# === Scenario Analysis (42 total scenarios) ===
# 
# 📁 **Basic Profiles** (12 scenarios)
#    Basic user profile scenarios (spending patterns, demographics)
#    - Young Professional - Tech Worker
#    - Business Traveler - Frequent Flyer
#    - Family Household - Suburban Lifestyle
# 
# 📁 **Portfolio Optimization** (8 scenarios)
#    Portfolio-level optimization and management scenarios
#    - Existing Card Holder - Chase Portfolio
#    - Multiple Cards - Optimization Needed
# 
# 📁 **Edge Cases** (15 scenarios)
#    Edge cases and boundary condition scenarios
#    - Amazon-only Spender - Minimal Categories
#    - Very Low Spending - Student Budget
```

### Example 2: Programmatic Category Analysis (Secondary Use Case)
Import and use individual functions for custom analysis workflows or integration with testing frameworks.

```python
from analyze_scenarios import load_scenarios, categorize_scenarios

# Load and categorize scenarios
scenarios_data = load_scenarios()
categories = categorize_scenarios(scenarios_data)

# Analyze category distribution
total_scenarios = sum(len(cat['scenarios']) for cat in categories.values())
print(f"Total scenarios: {total_scenarios}")

# Find categories with most/least coverage
category_counts = {name: len(data['scenarios']) for name, data in categories.items()}
most_covered = max(category_counts, key=category_counts.get)
least_covered = min(category_counts, key=category_counts.get)

print(f"Most covered category: {most_covered} ({category_counts[most_covered]} scenarios)")
print(f"Least covered category: {least_covered} ({category_counts[least_covered]} scenarios)")

# Extract scenarios for specific testing
edge_case_scenarios = categories['edge_cases']['scenarios']
for scenario in edge_case_scenarios:
    print(f"Edge case: {scenario['name']}")
```

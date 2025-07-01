# Data-Driven Testing Guide

This guide explains how to use the comprehensive data-driven test suite for credit card recommendations.

## ⚠️ Important: Test Data vs Production Data

The test suite creates its own isolated test data to avoid conflicts with your production database. Tests run in Django's test framework use a separate test database, so they won't interfere with your actual data.

However, the management command (`run_scenario`) runs against your actual database and may conflict with existing data. For production systems, consider using the Django test framework instead.

## Overview

The test suite allows you to define test scenarios with:
- **User spending profiles** - Monthly spending amounts by category
- **Credit cards owned** - Cards the user currently has
- **Available credit cards** - Cards in the system with their reward structures
- **Expected outputs** - What recommendations should be generated

## Test Files

### 1. `cards/test_data_driven.py`
Python-based test scenarios defined directly in code. Good for complex scenarios that need programmatic logic.

### 2. `cards/test_json_scenarios.py` 
JSON-based test scenarios loaded from external files. Easier to maintain and modify without changing code.

### 3. `data/tests/scenarios.json`
JSON file containing test scenario definitions. This is where you'll add most new scenarios.

### 4. `management/commands/run_scenario.py`
Django management command for running scenarios individually or in batches.

## Running Tests

### ✅ Recommended: Use Django Test Framework (Isolated Database)

The Django test framework automatically creates a separate test database, so your production data is never touched:

```bash
# Run all Python-defined scenarios
python manage.py test cards.test_data_driven

# Run all JSON-defined scenarios  
python manage.py test cards.test_json_scenarios

# Run both
python manage.py test cards.test_data_driven cards.test_json_scenarios

# Run specific test
python manage.py test cards.test_data_driven.CreditCardRecommendationScenarios.test_high_grocery_spender

# Run with detailed output
python manage.py test cards.test_json_scenarios -v 2
```

### ⚠️ Alternative: Management Command (Uses Production Database)

**Warning**: These commands run against your actual database and may conflict with existing data.

```bash
# List available scenarios
python manage.py run_scenario --list

# Run a specific scenario (against production DB)
python manage.py run_scenario "Young Professional - Dining Focus"

# Run all scenarios with detailed output (against production DB)
python manage.py run_scenario --all --verbose
```

### 🔒 Database Isolation

- **Django Tests**: Create isolated test database → Run tests → Destroy test database
- **Management Command**: Runs against your production database (use with caution)

## Adding New Scenarios

### Method 1: Add to JSON File (Recommended)

Edit `data/tests/scenarios.json` and add a new scenario to the `scenarios` array:

```json
{
  "name": "Your Scenario Name",
  "description": "Brief description of what this tests",
  "user_profile": {
    "spending": {
      "groceries": 500,
      "dining": 300,
      "gas": 200,
      "travel": 100,
      "general": 400
    },
    "preferences": {
      "max_annual_fee": 100,
      "preferred_reward_type": "cashback"
    }
  },
  "owned_cards": ["Card Name If User Already Has It"],
  "available_cards": [
    {
      "name": "Test Card",
      "issuer": "chase",
      "annual_fee": 95,
      "signup_bonus_amount": 20000,
      "signup_bonus_type": "points",
      "primary_reward_type": "points",
      "metadata": {"reward_value_multiplier": 0.015},
      "reward_categories": [
        {
          "category": "dining",
          "rate": 3.0,
          "type": "points",
          "max_spend": 6000
        },
        {
          "category": "general",
          "rate": 1.0,
          "type": "points"
        }
      ]
    }
  ],
  "expected_recommendations": {
    "count": 1,
    "actions": ["apply"],
    "min_total_value": 200,
    "must_include_cards": ["Test Card"],
    "reasoning_must_contain": ["dining", "3.0x"]
  }
}
```

### Method 2: Add to Python Test File

Add to the `SCENARIOS` list in `cards/test_data_driven.py`:

```python
{
    'name': 'Your Scenario Name',
    'user_profile': {
        'spending': {
            'groceries': 500,
            'dining': 300,
            # ... other categories
        }
    },
    'owned_cards': [],
    'available_cards': [
        {
            'name': 'Test Card',
            'issuer': 'chase',
            # ... card details
        }
    ],
    'expected_recommendations': {
        'count': 1,
        'actions': ['apply'],
        # ... expectations
    }
}
```

## Scenario Structure

### User Profile
```json
"user_profile": {
  "spending": {
    "groceries": 500,    // Monthly amount
    "dining": 300,
    "gas": 200,
    "travel": 100,
    "general": 400       // Catch-all category
  },
  "preferences": {       // Optional
    "max_annual_fee": 100,
    "preferred_reward_type": "cashback"
  }
}
```

### Available Cards
```json
"available_cards": [
  {
    "name": "Card Name",
    "issuer": "chase",                    // chase, amex, capital_one
    "annual_fee": 95,
    "signup_bonus_amount": 20000,
    "signup_bonus_type": "points",        // points, miles, cashback
    "primary_reward_type": "points",
    "metadata": {
      "reward_value_multiplier": 0.015   // How much each point is worth
    },
    "reward_categories": [
      {
        "category": "dining",             // Must match spending categories
        "rate": 3.0,                      // Reward multiplier (3x points)
        "type": "points",
        "max_spend": 6000                 // Optional annual spending cap
      }
    ]
  }
]
```

### Expected Recommendations
```json
"expected_recommendations": {
  "count": 2,                           // Expected number of recommendations
  "actions": ["apply", "keep"],         // Actions that should be recommended
  "min_total_value": 500,              // Minimum total estimated value
  "must_include_cards": ["Card Name"], // Cards that must be recommended
  "reasoning_must_contain": [          // Text that must appear in reasoning
    "dining", "3.0x", "bonus"
  ]
}
```

## Available Categories

The following spending categories are available:
- `groceries` - Supermarkets and grocery stores
- `dining` - Restaurants and dining out  
- `gas` - Gas stations and fuel
- `travel` - Flights, hotels, and travel
- `general` - All other purchases (catch-all)

## Available Issuers

- `chase` - Chase Bank
- `amex` - American Express
- `capital_one` - Capital One

## Reward Types

- `points` - Transferable points (e.g., Chase Ultimate Rewards)
- `miles` - Airline miles
- `cashback` - Cash back rewards

## Example Scenarios

### High Grocery Spender
Tests recommendations for someone who spends heavily on groceries.

### Business Traveler  
Tests recommendations for high travel and dining spending.

### Existing Card Optimization
Tests whether the system recommends keeping or canceling existing cards.

### Family with Mixed Spending
Tests optimization across multiple spending categories.

## Validation

The test suite validates:

1. **Correct number of recommendations** - Ensures the right amount of cards are suggested
2. **Expected actions** - Verifies apply/keep/cancel recommendations
3. **Minimum reward values** - Ensures recommendations meet value thresholds  
4. **Specific card inclusion** - Checks that certain cards are recommended
5. **Reasoning content** - Validates that explanations contain expected keywords

## Best Practices

### Creating Good Scenarios

1. **Realistic spending** - Use realistic monthly amounts
2. **Clear objectives** - Each scenario should test a specific situation
3. **Diverse profiles** - Cover different spending patterns and user types
4. **Edge cases** - Include scenarios with unusual spending or card combinations
5. **Validation** - Always include expected outcomes to catch regressions

### Naming Conventions

- Use descriptive names that explain the scenario
- Include the key characteristic being tested
- Examples: "High Grocery Spender", "Business Traveler", "Fee Optimization"

### Expected Recommendations

- Set realistic expectations based on the spending profile
- Include minimum value thresholds to catch calculation errors
- Specify required cards when testing specific features
- Use reasoning validation to ensure explanations are correct

## Troubleshooting

### Common Issues

1. **Missing categories** - Ensure spending categories exist in the database
2. **Invalid issuers** - Check that issuer slugs match available options
3. **Calculation errors** - Verify reward multipliers and spending amounts
4. **Database state** - Tests run in isolation with fresh data each time

### Debugging

1. **Run with verbose output** - Use `--verbose` flag for detailed breakdowns
2. **Check individual scenarios** - Run one scenario at a time to isolate issues
3. **Validate JSON** - Ensure JSON files are valid and properly formatted
4. **Review logs** - Check Django logs for detailed error information

## Contributing

When adding new scenarios:

1. **Test locally** - Run your scenario to ensure it works
2. **Add documentation** - Include a clear description
3. **Set expectations** - Define what the scenario should accomplish
4. **Follow conventions** - Use consistent naming and structure
5. **Validate results** - Ensure expected outcomes are realistic

This testing framework makes it easy to validate that the recommendation engine works correctly across a wide variety of user profiles and card combinations.
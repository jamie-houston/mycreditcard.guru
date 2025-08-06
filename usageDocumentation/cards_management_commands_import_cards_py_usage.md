# import_cards.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/management/commands/import_cards.py` module, which contains a Django management command for importing credit card data from JSON files. This command provides bulk import functionality for credit cards, issuers, reward types, and related data with comprehensive validation, error handling, and progress reporting.

## Module Overview
`cards/management/commands/import_cards.py` is a Django management command module that implements the `import_cards` command for bulk data import operations. It provides structured import of credit card data from JSON files with proper data validation and relationship handling.

### Key Responsibilities:
- **Bulk Data Import**: Imports credit card data, issuers, reward types, and related models from structured JSON files with batch processing and validation
- **Data Validation & Error Handling**: Validates imported data for consistency, handles missing relationships, and provides detailed error reporting for import issues
- **Progress Reporting**: Provides command-line progress indicators, import statistics, and detailed logging for monitoring bulk import operations

## Initialization
Django management commands are automatically discovered and executed via Django's management framework. No manual initialization required.

```python
# Execute via Django management command:
# python manage.py import_cards --file data/input/cards/chase.json
# python manage.py import_cards --directory data/input/cards/
```

## Public API documentation

### Command Class
- **`Command`**: Django management command that inherits from `BaseCommand` for importing credit card data from JSON files

### Command Arguments
- **`--file <path>`**: Import cards from a specific JSON file
- **`--directory <path>`**: Import all JSON files from a directory
- **`--dry-run`**: Preview import without making database changes
- **`--verbose`**: Show detailed progress and validation information
- **`--force`**: Overwrite existing cards with matching names/issuers

### Import Features
- Bulk import of credit cards, issuers, reward types, and related data
- JSON file validation and structure checking
- Progress reporting with statistics and error handling
- Batch processing for efficient database operations
- Relationship validation and foreign key handling

## Dependencies
### External Dependencies:
- `django.core.management.base.BaseCommand`: Django management command framework
- `json`: JSON file parsing and validation
- `pathlib.Path`: File system operations

### Internal Dependencies:
- `cards.models`: All card-related models for data import
- Used by: Data migration scripts, initial setup, bulk data updates
- No web interface dependencies (pure command-line utility)

## Practical Code Examples

### Example 1: Basic Card Import Operations
How to import credit card data from JSON files.

```python
# Import cards from a single file
# python manage.py import_cards --file data/input/cards/chase.json

# Import all card files from directory
# python manage.py import_cards --directory data/input/cards/

# Dry run to preview changes without importing
# python manage.py import_cards --file chase.json --dry-run

# Verbose import with detailed progress
# python manage.py import_cards --directory cards/ --verbose

# Force overwrite existing cards
# python manage.py import_cards --file amex.json --force
```

### Example 2: JSON File Structure for Import
Expected JSON structure for credit card import files.

```python
# File: data/input/cards/chase.json
{
    "issuer": {
        "name": "Chase",
        "max_cards_rule": 5,
        "business_rule": "5/24"
    },
    "reward_types": [
        {"name": "Ultimate Rewards", "category": "Points"},
        {"name": "Cash Back", "category": "Cash"}
    ],
    "spending_categories": [
        {"name": "Travel", "description": "Airlines, hotels, car rentals"},
        {"name": "Dining", "description": "Restaurants and food delivery"}
    ],
    "cards": [
        {
            "name": "Chase Sapphire Preferred",
            "annual_fee": 95.00,
            "primary_reward_type": "Ultimate Rewards",
            "reward_categories": [
                {"category": "Travel", "rate": 2.0, "cap": null},
                {"category": "Dining", "rate": 2.0, "cap": null},
                {"category": "General", "rate": 1.0, "cap": null}
            ],
            "card_credits": [
                {"credit_type": "Signup Bonus", "amount": 60000, "description": "60,000 points after $4,000 spend in 3 months"}
            ]
        }
    ]
}

# Command validates:
# - JSON structure and required fields
# - Issuer and reward type relationships
# - Spending category references
# - Numeric values and constraints
# - Prevents duplicate entries (unless --force used)
```

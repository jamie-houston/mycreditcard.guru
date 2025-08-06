# import_spending_credits.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/management/commands/import_spending_credits.py` module, which contains a Django management command for importing spending credit data from JSON files. This command provides bulk import functionality for credit types, card credits, and spending credit definitions with comprehensive validation, error handling, and progress reporting.

## Module Overview
`cards/management/commands/import_spending_credits.py` is a Django management command module that implements the `import_spending_credits` command for bulk data import operations. It provides structured import of spending credit data from JSON files with proper data validation and relationship handling.

### Key Responsibilities:
- **Bulk Credit Data Import**: Imports spending credit types, card credits, and credit definitions from structured JSON files with batch processing and validation
- **Data Validation & Error Handling**: Validates imported credit data for consistency, handles missing relationships, and provides detailed error reporting for import issues
- **Progress Reporting**: Provides command-line progress indicators, import statistics, and detailed logging for monitoring bulk import operations

## Initialization
Django management commands are automatically discovered and executed via Django's management framework. No manual initialization required.

```python
# Execute via Django management command:
# python manage.py import_spending_credits --file data/input/system/spending_credits.json
# python manage.py import_spending_credits --directory data/input/credits/
```

## Public API documentation

### Command Class
- **`Command`**: Django management command that inherits from `BaseCommand` for importing spending credit data from JSON files

### Command Arguments
- **`--file <path>`**: Import spending credits from a specific JSON file
- **`--directory <path>`**: Import all JSON files from a directory
- **`--dry-run`**: Preview import without making database changes
- **`--verbose`**: Show detailed progress and validation information
- **`--force`**: Overwrite existing credits with matching names/types

### Import Features
- Bulk import of credit types, card credits, and spending credit definitions
- JSON file validation and structure checking
- Progress reporting with statistics and error handling
- Batch processing for efficient database operations
- Relationship validation between cards and credit types

## Dependencies
### External Dependencies:
- `django.core.management.base.BaseCommand`: Django management command framework
- `json`: JSON file parsing and validation
- `pathlib.Path`: File system operations

### Internal Dependencies:
- `cards.models`: CreditType, CardCredit models for data import
- Used by: Data migration scripts, credit system setup, bulk credit updates
- No web interface dependencies (pure command-line utility)

## Practical Code Examples

### Example 1: Basic Spending Credit Import Operations
How to import spending credit data from JSON files.

```python
# Import credits from a single file
# python manage.py import_spending_credits --file data/input/system/spending_credits.json

# Import all credit files from directory
# python manage.py import_spending_credits --directory data/input/credits/

# Dry run to preview changes without importing
# python manage.py import_spending_credits --file credits.json --dry-run

# Verbose import with detailed progress
# python manage.py import_spending_credits --directory credits/ --verbose

# Force overwrite existing credits
# python manage.py import_spending_credits --file new_credits.json --force
```

### Example 2: JSON File Structure for Spending Credits Import
Expected JSON structure for spending credit import files.

```python
# File: data/input/system/spending_credits.json
{
    "credit_types": [
        {
            "name": "Signup Bonus",
            "category": "Welcome Offer",
            "description": "Points or cash earned after meeting initial spending requirement"
        },
        {
            "name": "Annual Travel Credit", 
            "category": "Statement Credit",
            "description": "Annual credit for travel purchases"
        },
        {
            "name": "Airport Lounge Access",
            "category": "Benefit",
            "description": "Complimentary access to airport lounges"
        }
    ],
    "card_credits": [
        {
            "card_name": "Chase Sapphire Preferred",
            "credit_type": "Signup Bonus",
            "amount": 60000,
            "description": "60,000 points after $4,000 spend in 3 months",
            "terms": "Valid for new cardholders only"
        },
        {
            "card_name": "Chase Sapphire Reserve",
            "credit_type": "Annual Travel Credit",
            "amount": 300,
            "description": "$300 annual travel credit",
            "terms": "Automatic statement credit for travel purchases"
        }
    ]
}

# Command validates:
# - JSON structure and required fields
# - Credit type definitions and categories
# - Card name references (must exist in database)
# - Numeric amounts and descriptions
# - Prevents duplicate credit assignments
```

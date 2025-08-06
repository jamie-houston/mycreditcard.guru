# import_credit_types.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/management/commands/import_credit_types.py` module, which contains a Django management command for importing credit type definitions from JSON files. This command provides bulk import functionality for spending credit type categories with comprehensive validation, error handling, and progress reporting for the credit system foundation.

## Module Overview
`cards/management/commands/import_credit_types.py` is a Django management command module that implements the `import_credit_types` command for bulk import operations. It provides structured import of credit type definitions from JSON files with proper data validation and category handling.

### Key Responsibilities:
- **Credit Type Definition Import**: Imports credit type categories, descriptions, and classification data from structured JSON files with batch processing and validation
- **Data Validation & Error Handling**: Validates imported credit type data for consistency, handles duplicate entries, and provides detailed error reporting for import issues
- **Progress Reporting**: Provides command-line progress indicators, import statistics, and detailed logging for monitoring credit type import operations

## Initialization
Django management commands are automatically discovered and executed via Django's management framework. No manual initialization required.

```python
# Execute via Django management command:
# python manage.py import_credit_types --file data/input/system/credit_types.json
# python manage.py import_credit_types --directory data/input/types/
```

## Public API documentation

### Command Class
- **`Command`**: Django management command that inherits from `BaseCommand` for importing credit type definitions from JSON files

### Command Arguments
- **`--file <path>`**: Import credit types from a specific JSON file
- **`--directory <path>`**: Import all JSON files from a directory
- **`--dry-run`**: Preview import without making database changes
- **`--verbose`**: Show detailed progress and validation information
- **`--force`**: Overwrite existing credit types with matching names

### Import Features
- Bulk import of credit type definitions and categories
- JSON file validation and structure checking
- Progress reporting with statistics and error handling
- Batch processing for efficient database operations
- Duplicate detection and handling with optional overwrite

## Dependencies
### External Dependencies:
- `django.core.management.base.BaseCommand`: Django management command framework
- `json`: JSON file parsing and validation
- `pathlib.Path`: File system operations

### Internal Dependencies:
- `cards.models.CreditType`: Credit type model for data import
- Used by: Credit system initialization, data migration scripts, type definition updates
- No web interface dependencies (pure command-line utility)

## Practical Code Examples

### Example 1: Basic Credit Type Import Operations
How to import credit type definitions from JSON files.

```python
# Import credit types from a single file
# python manage.py import_credit_types --file data/input/system/credit_types.json

# Import all type files from directory
# python manage.py import_credit_types --directory data/input/types/

# Dry run to preview changes without importing
# python manage.py import_credit_types --file types.json --dry-run

# Verbose import with detailed progress
# python manage.py import_credit_types --directory types/ --verbose

# Force overwrite existing credit types
# python manage.py import_credit_types --file updated_types.json --force
```

### Example 2: JSON File Structure for Credit Types Import
Expected JSON structure for credit type definition import files.

```python
# File: data/input/system/credit_types.json
{
    "credit_types": [
        {
            "name": "Signup Bonus",
            "category": "Welcome Offer",
            "description": "Initial bonus points or cash earned after meeting spending requirement within specified timeframe",
            "typical_value_range": "50000-100000 points or $200-$1000 cash",
            "duration": "Usually first 3-6 months"
        },
        {
            "name": "Annual Travel Credit",
            "category": "Statement Credit", 
            "description": "Annual credit applied to travel purchases automatically",
            "typical_value_range": "$100-$300 annually",
            "duration": "Annual renewal"
        },
        {
            "name": "Airport Lounge Access",
            "category": "Travel Benefit",
            "description": "Complimentary access to airport lounges worldwide",
            "typical_value_range": "$50-$100 per visit value",
            "duration": "While cardholder"
        },
        {
            "name": "Free Checked Bag",
            "category": "Travel Benefit",
            "description": "Waived fees for checked baggage on eligible airlines",
            "typical_value_range": "$30-$60 per bag",
            "duration": "Per qualifying trip"
        }
    ]
}

# Command validates:
# - JSON structure and required fields
# - Credit type name uniqueness
# - Category consistency and classification
# - Description completeness and formatting
# - Value range and duration information
# - Prevents duplicate type definitions (unless --force used)
```

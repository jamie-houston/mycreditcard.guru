# convert_cards_data.py Usage Documentation

## Executive Summary
The `convert_cards_data.py` module is a data migration utility that transforms legacy credit card data from a monolithic JSON format into organized, issuer-specific files compatible with the Django application. It performs data normalization, reward type mapping, and structural transformations to ensure seamless integration with the Credit Card Guru data models.

## Module Overview
`convert_cards_data.py` is a command-line data transformation script that processes raw credit card data exports and converts them into the standardized format expected by the Django application's import system. It handles data mapping, validation, and organization for efficient bulk data migration.

### Key Responsibilities:
- **Data Structure Transformation**: Converts legacy data format to Django-compatible JSON structure with proper field mapping and type conversion
- **Issuer Organization**: Groups credit cards by issuer and creates separate files for organized data management and selective importing
- **Reward System Mapping**: Analyzes card features to determine reward types (Cashback/Miles/Points) and calculates appropriate value multipliers

## Initialization
The script operates on a hardcoded input file (`data/input/data.json`) and outputs to the `data/input/` directory. It's designed for one-time or periodic data migration tasks.

```python
# Run from command line (primary usage)
python convert_cards_data.py

# Or import and use programmatically
from convert_cards_data import convert_card, map_issuer_name
converted = convert_card(raw_card_data)
issuer = map_issuer_name('AMERICAN_EXPRESS')
```

## Public API documentation

### `map_issuer_name(issuer)`
Normalizes issuer names from various formats to consistent display names.
- **Parameters**: `issuer` (str) - Raw issuer identifier (e.g., 'AMERICAN_EXPRESS')
- **Returns**: String with properly formatted issuer name (e.g., 'American Express')
- **Features**: Handles underscore-separated names and provides fallback formatting

### `map_reward_type(card_data)`
Determines the reward type category based on card characteristics.
- **Parameters**: `card_data` (dict) - Card data dictionary with features
- **Returns**: String - 'Cashback', 'Miles', or 'Points'
- **Logic**: Uses `universalCashbackPercent` presence and name pattern matching

### `extract_reward_categories(card_data)`
Extracts and formats reward category information from card data.
- **Parameters**: `card_data` (dict) - Card data with reward information
- **Returns**: List of category dictionaries with reward rates
- **Note**: Currently handles universal cashback; designed for future category expansion

### `convert_card(card_data)`
Main transformation function that converts a single card from legacy to Django format.
- **Parameters**: `card_data` (dict) - Raw card data in legacy format
- **Returns**: Dict with standardized card structure for Django import
- **Features**: 
  - Signup bonus extraction and calculation
  - Reward value multiplier assignment
  - Card type detection (business/personal)
  - Network normalization

### `main()`
Orchestrates the complete conversion process from input file to organized output files.
- **Process**: 
  1. Reads `data/input/data.json`
  2. Converts each non-discontinued card
  3. Groups cards by issuer
  4. Writes separate JSON files per issuer
  5. Reports conversion statistics

## Dependencies

### External Dependencies
- **json**: JSON file reading, writing, and data manipulation
- **os**: File system operations and path validation
- **collections.defaultdict**: Efficient issuer grouping data structure

### Internal Dependencies
- **File Structure**: Requires `data/input/data.json` source file
- **Output Directory**: Creates files in `data/input/` for subsequent import processes

## Practical Code Examples

### Example 1: Complete Data Migration (Primary Use Case)
Use this when migrating from legacy credit card data sources to the Django application format.

```python
# Run complete migration process
python convert_cards_data.py

# Expected output:
# Reading data/input/data.json...
# Found 247 cards
# Skipping discontinued card: Chase Sapphire (Original)
# Writing 15 cards to data/input/chase.json
# Writing 12 cards to data/input/american_express.json
# Writing 8 cards to data/input/citi.json
# ...
# Conversion complete! Created files for 8 issuers:
#   - chase.json (15 cards)
#   - american_express.json (12 cards)
#   - citi.json (8 cards)
```

### Example 2: Programmatic Card Conversion (Secondary Use Case)
Use individual functions for custom data processing workflows or testing specific transformations.

```python
from convert_cards_data import convert_card, map_issuer_name, map_reward_type

# Test issuer name mapping
issuer = map_issuer_name('CAPITAL_ONE')  # Returns 'Capital One'

# Process individual card
raw_card = {
    'name': 'Chase Sapphire Preferred',
    'issuer': 'CHASE',
    'annualFee': 95,
    'universalCashbackPercent': 0,
    'offers': [{'amount': [{'amount': 60000}], 'spend': 4000, 'days': 90}]
}

converted_card = convert_card(raw_card)
print(converted_card['reward_type'])  # 'Points'
print(converted_card['signup_bonus']['bonus_amount'])  # 60000

# Determine reward type
reward_type = map_reward_type(raw_card)  # 'Points'
```

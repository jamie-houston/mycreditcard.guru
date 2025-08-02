# Test Setup Data

This directory contains **test-only** setup data used by the `run_scenario` command and test suites.

⚠️ **Important**: This data is completely separate from production system data in `data/input/system/`. Test-specific issuers like "Generic Bank", "Premium Bank", and "Basic Bank" exist only here and should never be mixed with production issuer data.

## Files

### `issuers.json`
Defines test credit card issuers including the required "Generic Bank" issuer used by test cards.

### `reward_types.json`
Defines reward types (Points, Miles, Cashback, etc.) used by test credit cards.

### `spending_categories.json`
Defines spending categories used in test scenarios and credit card reward definitions.

## Usage

The `run_scenario` command automatically loads this test setup data when running scenarios. If you run scenarios and see errors about missing issuers, reward types, or spending categories, these files provide the necessary test data.

## Structure

Each file follows a simple JSON array format:

```json
[
  {
    "name": "Example Name",
    "field1": "value1",
    "field2": "value2"
  }
]
```

## Automatic Loading

Test setup data is automatically loaded by:
- `python manage.py run_scenario` command
- Django test cases that extend `JSONScenarioTestBase`

No manual import is required - the system creates these records in the database as needed during test execution.
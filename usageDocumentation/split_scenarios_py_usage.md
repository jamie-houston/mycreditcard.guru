# split_scenarios.py Usage Documentation

## Executive Summary
The `split_scenarios.py` module is a data organization utility that categorizes and splits large scenario test files into smaller, themed JSON files for better test management. It analyzes scenario names using pattern matching to automatically organize test cases by functionality (basic profiles, portfolio optimization, edge cases, etc.) and generates an index file for easy navigation.

## Module Overview
`split_scenarios.py` is a command-line data processing script that transforms monolithic test scenario files into organized, categorized collections. It serves as a test data management tool for the Credit Card Guru application's testing infrastructure.

### Key Responsibilities:
- **Scenario Categorization**: Analyzes scenario names using regex patterns to automatically classify test cases into 7 predefined categories
- **File Generation**: Creates separate JSON files for each category with proper metadata and descriptions
- **Index Management**: Generates a comprehensive index file listing all created scenario files with statistics and metadata

## Initialization
This script is designed to be run directly from the command line in the project root directory. It requires the source scenarios.json file to exist in the expected location and automatically creates output directories as needed.

```python
# Run from command line (most common usage)
python split_scenarios.py

# Or import and run programmatically
from split_scenarios import load_scenarios, categorize_scenarios, write_scenario_files
scenarios = load_scenarios()
categories = categorize_scenarios(scenarios)
files_created = write_scenario_files(categories, 'custom/output/path')
```

## Public API documentation

### `load_scenarios()`
Loads scenario data from the predefined JSON file location.
- **Parameters**: None (hardcoded to `data/tests/scenarios.json`)
- **Returns**: Dict containing the full scenarios JSON structure
- **Raises**: FileNotFoundError if scenarios.json doesn't exist

### `categorize_scenarios(scenarios_data)`
Analyzes scenario names and categorizes them into 7 predefined themes using pattern matching.
- **Parameters**: `scenarios_data` (dict) - The loaded scenarios JSON structure
- **Returns**: Dict with category keys containing scenarios lists and metadata
- **Categories**: basic_profiles, portfolio_optimization, zero_fee_cards, spending_credits, card_count_optimization, edge_cases, signup_bonus

### `write_scenario_files(categories, output_dir)`
Creates individual JSON files for each category with scenarios and metadata.
- **Parameters**: 
  - `categories` (dict) - Categorized scenarios from categorize_scenarios()
  - `output_dir` (str) - Target directory for generated files
- **Returns**: List of dicts with file creation metadata (filename, count, category)
- **Side Effects**: Creates directory structure and JSON files

### `create_index_file(files_created, output_dir)`
Generates a comprehensive index file listing all created scenario files with statistics.
- **Parameters**:
  - `files_created` (list) - Metadata from write_scenario_files()
  - `output_dir` (str) - Target directory for index file
- **Returns**: String path to created index.json file
- **Features**: Includes total counts, descriptions, and file metadata

## Dependencies

### External Dependencies
Based on knowledge graph analysis (`module(split_scenarios.py) -> imports -> *`):
- **json**: JSON file reading and writing operations
- **os**: File system operations and directory creation
- **re**: Regular expression pattern matching for scenario categorization
- **collections**: defaultdict for efficient data structure management

### Internal Dependencies
- **File System Requirements**: 
  - Source file: `data/tests/scenarios.json` (must exist)
  - Output directory: `data/input/tests/scenarios/` (created automatically)
- **No Django Dependencies**: Pure Python script, independent of Django framework

## Practical Code Examples

### Example 1: Full Scenario Splitting (Primary Use Case)
Use this when you have a large scenarios.json file that needs to be organized into manageable, themed test files for better test organization and maintenance.

```python
# From command line - most common usage
python split_scenarios.py

# Expected output:
# 📥 Loaded 45 scenarios from data/tests/scenarios.json
# ✅ Created basic_profiles.json with 12 scenarios
# ✅ Created portfolio_optimization.json with 8 scenarios
# ✅ Created edge_cases.json with 15 scenarios
# ✅ Created spending_credits.json with 6 scenarios
# ✅ Created index.json with 4 scenario files
# 🎉 Successfully split scenarios into 4 files in data/input/tests/scenarios/
```

### Example 2: Programmatic Usage with Custom Output (Secondary Use Case)
Import and use individual functions for custom processing workflows or integration with other data processing pipelines.

```python
from split_scenarios import load_scenarios, categorize_scenarios, write_scenario_files, create_index_file

# Load and process scenarios
scenarios_data = load_scenarios()
print(f"Loaded {len(scenarios_data['scenarios'])} scenarios")

# Categorize scenarios
categories = categorize_scenarios(scenarios_data)

# Write to custom location
custom_output = 'tests/custom_scenarios/'
files_created = write_scenario_files(categories, custom_output)

# Create index
index_path = create_index_file(files_created, custom_output)
print(f"Created index at: {index_path}")

# Analyze categorization results
for cat_name, cat_data in categories.items():
    if cat_data['scenarios']:
        print(f"{cat_name}: {len(cat_data['scenarios'])} scenarios")
```

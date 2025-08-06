# scenario_loader.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/scenario_loader.py` module, which provides utility classes for loading test scenarios from multiple JSON files. The ScenarioLoader class offers centralized scenario management for the testing framework, ensuring consistency across test files and providing flexible loading from both single files and directory structures.

## Module Overview
`cards/scenario_loader.py` is a 141-line utility module containing the ScenarioLoader class that handles loading and combining test scenarios from JSON files. It supports both single file loading and directory-based loading with intelligent file discovery and metadata extraction for comprehensive test scenario management.

### Key Responsibilities:
- **Flexible Scenario Loading**: Loads scenarios from single JSON files or entire directories with automatic file discovery and combination
- **Data Validation & Error Handling**: Provides robust JSON parsing with detailed error messages and validation of scenario file structures  
- **Metadata Management**: Extracts and combines metadata from multiple scenario files including file descriptions, categories, and scenario counts

## Initialization
Import and use the utility functions directly. No class instantiation required.

```python
from cards.scenario_loader import load_scenarios_from_file, load_scenarios_from_directory

# Load scenarios from a single file
scenarios = load_scenarios_from_file('data/tests/scenarios/basic_profiles.json')

# Load scenarios from entire directory
all_scenarios = load_scenarios_from_directory('data/tests/scenarios/')
```

## Public API documentation

### Core Functions
- **`load_scenarios_from_file(file_path)`**: Loads test scenarios from a single JSON file with validation and error handling
- **`load_scenarios_from_directory(directory_path)`**: Loads scenarios from all JSON files in a directory with recursive discovery
- **`validate_scenario_structure(scenario)`**: Validates scenario data structure and required fields
- **`get_scenario_metadata(file_path)`**: Extracts metadata from scenario files including file info and scenario counts

### Data Validation Features
- JSON parsing with comprehensive error handling
- Scenario structure validation (user_profile, expected_results, etc.)
- File existence and readability checks
- Automatic metadata extraction and logging

### Flexible Loading Options
- Single file loading for specific test cases
- Directory loading for batch test execution
- Recursive directory scanning for organized test suites
- Filtering and selection capabilities for targeted testing

## Dependencies
### External Dependencies:
- `json`: JSON file parsing and validation
- `pathlib.Path`: File system operations and path handling
- `logging`: Error reporting and debugging information

### Internal Dependencies:
- Used by: `cards.test_json_scenarios`, `cards.test_data_driven`
- Used by: Test automation scripts, scenario validation utilities
- No internal model dependencies (pure utility module)

## Practical Code Examples

### Example 1: Loading Scenarios for Testing
How to load and use scenarios in test cases.

```python
from cards.scenario_loader import load_scenarios_from_file, validate_scenario_structure

# Load scenarios from specific file
scenarios = load_scenarios_from_file('data/tests/scenarios/travel_rewards.json')

for scenario in scenarios:
    # Validate scenario structure
    if validate_scenario_structure(scenario):
        print(f"Running scenario: {scenario['name']}")
        
        # Extract user profile data
        spending = scenario['user_profile']['spending']
        preferences = scenario['user_profile']['preferences']
        
        # Run through recommendation engine
        # recommendations = engine.get_recommendations(spending, preferences)
        
        # Validate against expected results
        expected = scenario['expected_results']
        # assert len(recommendations) >= expected['min_recommendations']

# Handle loading errors gracefully
try:
    scenarios = load_scenarios_from_file('invalid_file.json')
except FileNotFoundError:
    print("Scenario file not found")
except json.JSONDecodeError:
    print("Invalid JSON format in scenario file")
```

### Example 2: Batch Loading and Organization
How to load scenarios from directories for comprehensive testing.

```python
from cards.scenario_loader import load_scenarios_from_directory, get_scenario_metadata

# Load all scenarios from test directory
base_dir = 'data/tests/scenarios/'
all_scenarios = load_scenarios_from_directory(base_dir)

print(f"Loaded {len(all_scenarios)} total scenarios")

# Get metadata for organization
for file_path in Path(base_dir).glob('*.json'):
    metadata = get_scenario_metadata(file_path)
    print(f"File: {metadata['file_name']}")
    print(f"  Scenarios: {metadata['scenario_count']}")
    print(f"  File size: {metadata['file_size']} bytes")
    print(f"  Categories: {metadata.get('categories', 'Unknown')}")

# Filter scenarios by type or category
travel_scenarios = [s for s in all_scenarios if 'travel' in s['name'].lower()]
cashback_scenarios = [s for s in all_scenarios if 'cash back' in s.get('description', '').lower()]

print(f"Travel scenarios: {len(travel_scenarios)}")
print(f"Cash back scenarios: {len(cashback_scenarios)}")
```

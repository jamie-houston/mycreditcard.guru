# setup_data.py Usage Documentation

## Executive Summary
The `setup_data.py` module is a Django data initialization script that automates the loading of essential application data after database migrations. It systematically imports system configurations, credit card data from multiple issuers, and credit type definitions to bootstrap the Credit Card Guru application with a complete dataset for production or development use.

## Module Overview
`setup_data.py` is a command-line utility script that serves as a data bootstrapping tool for the Django application. It contains two main functions that coordinate the systematic loading of JSON fixtures and management command execution.

### Key Responsibilities:
- **Data Loading Orchestration**: Manages the sequential loading of system data (spending categories, issuers, reward types) from JSON fixtures
- **Credit Card Import Automation**: Discovers and imports credit card data from multiple issuer files in the `data/input/cards/` directory
- **Error Handling & Reporting**: Provides robust subprocess execution with detailed success/failure reporting and progress tracking

## Initialization
This script is designed to be run directly from the command line in the project root directory. It requires Django's `manage.py` to be present and executes various management commands through subprocess calls.

```python
# Run from command line in project root
python setup_data.py

# Or import and run programmatically
from setup_data import main
main()
```

## Public API documentation

### `run_command(command, description)`
Executes a shell command using subprocess and provides formatted output with error handling.
- **Parameters**: 
  - `command` (str): Shell command to execute
  - `description` (str): Human-readable description for progress reporting
- **Returns**: Boolean indicating success/failure
- **Features**: Captures output, shows last 3 lines of stdout, handles errors gracefully

### `main()`
Main orchestration function that coordinates the entire data loading process.
- **Parameters**: None
- **Returns**: None (exits with status code on failure)
- **Process**: 
  1. Validates environment (manage.py presence, virtual env warning)
  2. Loads system data from JSON fixtures
  3. Discovers and imports credit card files
  4. Imports credit types via management command
  5. Provides comprehensive summary and next steps

## Dependencies

### External Dependencies
Based on knowledge graph analysis (`module(setup_data.py) -> imports -> *`):
- **os**: File system operations and environment variable access
- **sys**: System-specific parameters and exit functionality
- **subprocess**: Shell command execution with error handling
- **glob**: File pattern matching for discovering card files
- **pathlib**: Modern path manipulation utilities

### Internal Dependencies
- **Django Management Commands**: 
  - `loaddata` - For loading JSON fixtures
  - `import_cards` - Custom command for credit card data import
  - `import_credit_types` - Custom command for credit type import
- **File Structure Dependencies**: Requires specific directory structure (`data/input/system/`, `data/input/cards/`)

## Practical Code Examples

### Example 1: Fresh Database Setup (Primary Use Case)
Use this after running `python manage.py migrate` on a fresh database to populate it with all necessary data for the Credit Card Guru application.

```python
# From command line - most common usage
python setup_data.py

# Expected output:
# 🚀 Setting up Credit Card Guru with initial data...
# 🔄 Loading spending_categories.json...
# ✅ Loading spending_categories.json completed successfully
# 🔄 Loading issuers.json...
# ✅ Loading issuers.json completed successfully
# ...
# 🎉 All data loaded successfully!
```

### Example 2: Programmatic Integration (Secondary Use Case)
Import and run the setup process from within another Python script or Django management command.

```python
import os
import sys
from setup_data import main, run_command

# Set working directory to project root if needed
os.chdir('/path/to/creditcard_guru/')

# Run full setup
try:
    main()
    print("Data setup completed successfully")
except SystemExit as e:
    if e.code != 0:
        print(f"Setup failed with exit code: {e.code}")

# Or run individual commands
success = run_command(
    'python manage.py loaddata data/input/system/issuers.json',
    'Loading issuer data'
)
```

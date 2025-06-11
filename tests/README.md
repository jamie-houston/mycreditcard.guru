# Testing Guide

The Credit Card Roadmap project includes comprehensive tests for both the core functionality and the Flask web application. This guide covers everything you need to know about running and understanding the tests.

## Test Organization

Tests are organized in two main directories:

- `/tests` - Core functionality tests (web scraping, data extraction, category parsing)
- `/flask_app/tests` - Flask application tests (routes, models, database operations)

## Quick Start

The easiest way to run all tests is using the test runner script:

```bash
# From the project root directory
python scripts/run_tests.py
```

## Running Tests

### Using the Test Runner Script (Recommended)

For convenience, use the included test runner script:

```bash
# Run all tests with nice formatting
python scripts/run_tests.py

# Run with verbose output
python scripts/run_tests.py --verbose

# Run with coverage report
python scripts/run_tests.py --coverage

# Run only core tests
python scripts/run_tests.py --core-only

# Run only Flask app tests
python scripts/run_tests.py --flask-only

# Run tests matching a pattern
python scripts/run_tests.py --pattern "test_category"

# See all options
python scripts/run_tests.py --help
```

### Using pytest Directly

From the base directory, you can also run tests using pytest directly:

```bash
# Run all tests (both core and Flask app tests)
python -m pytest tests/ flask_app/tests/

# Run only core functionality tests
python -m pytest tests/

# Run only Flask application tests
python -m pytest flask_app/tests/

# Run tests with verbose output
python -m pytest tests/ flask_app/tests/ -v

# Run specific test file
python -m pytest tests/test_extraction.py

# Run tests matching a pattern
python -m pytest -k "test_category" tests/ flask_app/tests/

# Run tests with coverage report (if coverage is installed)
python -m pytest tests/ flask_app/tests/ --cov=app --cov=scripts
```

## Test Categories

### Core Tests (`/tests`)

**`test_extraction.py`** - NerdWallet data extraction and web scraping
- Tests the core web scraping functionality
- Validates data extraction from NerdWallet pages
- Ensures proper handling of HTML parsing

**`test_category_bonuses.py`** - Credit card category parsing and bonus detection
- Tests parsing of reward categories from scraped data
- Validates bonus category detection algorithms
- Covers edge cases in category text parsing
- Tests for various credit card issuers (Chase, Amex, Capital One, etc.)

### Flask App Tests (`/flask_app/tests`)

**`test_models.py`** - Database model functionality
- Tests all SQLAlchemy models
- Validates model relationships and constraints
- Tests model methods and properties

**`test_routes.py`** - Web route testing
- Tests all Flask routes and endpoints
- Validates request/response handling
- Tests authentication and authorization

**`test_routes_health.py`** - Application health and integration tests
- End-to-end testing of key user flows
- Health check endpoints
- Integration testing across multiple components

**`test_card_import.py`** - Credit card import functionality
- Tests the card import system
- Validates data transformation and mapping
- Tests error handling during imports

**`test_user_model.py`** - User authentication and management
- Tests user creation and authentication
- Validates password hashing and verification
- Tests user roles and permissions

**`test_field_mapper.py`** - Data field mapping utilities
- Tests the field mapping system used during imports
- Validates data transformation logic
- Tests handling of various data formats

## Test Configuration

### Flask App Configuration

The Flask app tests use a pytest configuration file (`flask_app/pytest.ini`) that:
- Filters out deprecation warnings for cleaner output
- Sets up proper test discovery patterns
- Configures strict marker and config validation

### Test Database

Flask app tests use an in-memory SQLite database for fast, isolated testing. Each test gets a fresh database instance to ensure test independence.

## Prerequisites

Make sure you have pytest installed (it's included in `requirements.txt`):

```bash
pip install -r requirements.txt
```

For coverage reports, you may also want to install pytest-cov:

```bash
pip install pytest-cov
```

## Writing New Tests

### Core Tests

When adding new core functionality (web scraping, data processing), add tests to the `/tests` directory:

```python
# tests/test_new_feature.py
def test_new_functionality():
    """Test description."""
    # Your test code here
    assert expected_result == actual_result
```

### Flask App Tests

When adding new Flask functionality, add tests to `/flask_app/tests`:

```python
# flask_app/tests/test_new_routes.py
import unittest
from app import create_app, db

class NewRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_new_route(self):
        """Test new route functionality."""
        response = self.client.get('/new-route')
        self.assertEqual(response.status_code, 200)
```

## Continuous Integration

The test runner script returns appropriate exit codes for CI/CD integration:
- Exit code 0: All tests passed
- Exit code 1: Some tests failed

This makes it easy to integrate with CI systems:

```bash
# In your CI script
python scripts/run_tests.py
if [ $? -eq 0 ]; then
    echo "Tests passed, proceeding with deployment"
else
    echo "Tests failed, stopping deployment"
    exit 1
fi
```

## Troubleshooting

### Common Issues

**Import Errors**: Make sure you're running tests from the project root directory and that all dependencies are installed.

**Database Errors**: Flask app tests create their own test database. If you see database-related errors, ensure SQLAlchemy is properly configured.

**Skipped Tests**: Some tests may be skipped if certain conditions aren't met (e.g., missing test data files). This is normal and expected.

### Getting Help

If you encounter issues with tests:
1. Run with verbose output: `python scripts/run_tests.py --verbose`
2. Check the specific test file that's failing
3. Ensure all dependencies are installed
4. Verify you're running from the correct directory

## Test Coverage

To see how much of your code is covered by tests:

```bash
python scripts/run_tests.py --coverage
```

This will show a detailed coverage report highlighting which lines of code are tested and which aren't. 
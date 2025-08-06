# manage.py Usage Documentation

## Executive Summary
The `manage.py` module is Django's standard command-line utility that provides access to administrative tasks and custom management commands for the Credit Card Guru application. It serves as the primary interface for database operations, development server management, testing, and custom data import workflows.

## Module Overview
`manage.py` is Django's auto-generated command-line interface script that bootstraps the Django environment and delegates command execution to Django's management system. It acts as the entry point for all administrative and development operations.

### Key Responsibilities:
- **Django Environment Bootstrap**: Sets up the Django settings module and imports the management framework
- **Command-Line Interface**: Provides access to built-in Django commands (runserver, migrate, test, etc.) and custom management commands
- **Error Handling**: Manages Django import errors and provides helpful guidance for environment setup issues

## Initialization
This script is automatically created by Django and should be run directly from the command line. It requires a properly configured Django environment with dependencies installed.

```python
# Standard Django management commands
python manage.py runserver          # Start development server
python manage.py migrate           # Apply database migrations
python manage.py createsuperuser   # Create admin user
python manage.py test             # Run test suite

# Custom management commands (Credit Card Guru specific)
python manage.py import_cards data/input/cards/chase.json
python manage.py import_spending_credits
python manage.py import_credit_types
```

## Public API documentation

### `main()`
The primary function that configures Django environment and executes management commands.
- **Parameters**: None (uses sys.argv for command-line arguments)
- **Environment Setup**: Sets 'DJANGO_SETTINGS_MODULE' to 'creditcard_guru.settings'
- **Error Handling**: Provides informative ImportError messages for Django installation issues
- **Execution**: Delegates to Django's `execute_from_command_line()`

## Dependencies

### External Dependencies
- **os**: Environment variable management for Django settings
- **sys**: Command-line argument access via sys.argv
- **django.core.management**: Django's command execution framework

### Internal Dependencies
- **creditcard_guru.settings**: Django project settings module
- **Custom Management Commands**: Located in each app's management/commands/ directory

## Practical Code Examples

### Example 1: Development Workflow (Primary Use Case)
Common development tasks using manage.py for day-to-day development work.

```python
# Start development server
python manage.py runserver 8000

# Database operations
python manage.py makemigrations     # Create new migrations
python manage.py migrate           # Apply migrations
python manage.py dbshell           # Access database shell

# Testing and debugging
python manage.py test              # Run all tests
python manage.py shell             # Django shell for debugging
python manage.py check             # Check for issues

# Static files (for production)
python manage.py collectstatic     # Collect static files
```

### Example 2: Data Management Commands (Secondary Use Case)
Credit Card Guru specific commands for data import and management.

```python
# Import credit card data from specific issuers
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/american_express.json

# Import system configuration data
python manage.py import_spending_credits
python manage.py import_credit_types

# Load initial fixture data
python manage.py loaddata data/input/system/spending_categories.json
python manage.py loaddata data/input/system/issuers.json

# Custom scenario management
python manage.py run_scenario "Test Scenario Name"
```

# admin.py Usage Documentation

## Executive Summary
The `admin.py` module is a comprehensive Django project management command-line utility that automates development, deployment, and data management tasks for the Credit Card Guru application. It provides an interactive menu system and direct command execution for all common administrative operations including database setup, OAuth configuration, data import, and development server management.

## Module Overview
`admin.py` is a project administration script that serves as a centralized control interface for Django project lifecycle management. It combines environment setup, database operations, data import workflows, and development tools into a single, user-friendly command-line interface.

### Key Responsibilities:
- **Environment & Database Management**: Handles Django environment setup, database migrations, OAuth configuration, and complete project initialization
- **Data Import Orchestration**: Provides interactive and automated workflows for importing credit card data, system configurations, and maintaining data integrity
- **Development Workflow Support**: Integrates server management, testing, static file collection, and deployment readiness checks into streamlined commands

## Initialization
The script is designed to run directly from the command line with automatic environment setup. It can operate in interactive menu mode (no arguments) or direct command mode with specific tasks and arguments.

```python
# Interactive mode - shows menu for task selection
python admin.py

# Direct command mode - execute specific tasks
python admin.py setup              # Full project setup
python admin.py server --port 3000 # Run server on custom port
python admin.py import-sample      # Import all sample data
python admin.py test               # Run test suite
```

## Public API documentation

### Core Infrastructure Functions

#### `setup_environment()`
Configures Django environment variables and loads .env file settings.
- **Parameters**: None
- **Purpose**: Sets DJANGO_SETTINGS_MODULE and processes environment variables from .env file
- **Called**: Automatically at script startup

#### `run_command(command, description=None)`
Executes shell commands with error handling and user feedback.
- **Parameters**: 
  - `command` (str) - Shell command to execute
  - `description` (str, optional) - Human-readable task description
- **Returns**: subprocess.CompletedProcess result
- **Features**: Automatic error handling, progress indication, project root context

### Setup & Configuration Functions

#### `install_dependencies()`
Installs Python packages from requirements.txt.

#### `setup_database()`
Creates and applies Django database migrations.

#### `setup_google_oauth()`
Configures Google OAuth SocialApp using environment variables (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET).

#### `full_setup()`
Complete project initialization workflow including optional database wipe, dependency installation, database setup, OAuth configuration, and essential data import.

### Data Management Functions

#### `import_sample_data()`
Interactive data import interface that discovers JSON files in data/input directories and provides organized import workflows with progress tracking.

#### `import_data(file_path)`
Direct import of specific credit card data file.

### Database Operations

#### `flush_database()`
Removes all data while preserving database structure (with user confirmation).

#### `wipe_database()`
Complete database and migration file removal for fresh start (requires 'WIPE' confirmation).

### Development & Deployment Functions

#### `run_server(port=8000)`
Starts Django development server on specified port.

#### `run_tests()`
Executes Django test suite.

#### `collect_static()`
Collects static files for production deployment.

#### `check_deployment()`
Validates deployment configuration and settings.

### Utility Functions

#### `show_interactive_menu()`
Displays user-friendly menu interface for common workflows.

#### `show_all_commands()`
Lists all available commands with descriptions.

#### `execute_task(task, args=None)`
Dispatcher function that maps task names to their corresponding functions.

## Dependencies

### External Dependencies
- **os**: Environment variable management and file system operations
- **sys**: System-specific parameters and exit handling
- **subprocess**: Shell command execution with error handling
- **argparse**: Command-line argument parsing and help generation
- **pathlib**: Modern path manipulation and file discovery

### Django Dependencies
- **django**: Core Django framework (setup and configuration)
- **allauth.socialaccount.models.SocialApp**: OAuth provider configuration
- **django.contrib.sites.models.Site**: Django sites framework integration

### Internal Dependencies
- **Django Management Commands**: Integrates with `import_cards`, `import_spending_credits`, and other custom commands
- **Environment Files**: Requires `.env` file for OAuth configuration and optional environment variables

## Practical Code Examples

### Example 1: Complete Project Setup (Primary Use Case)
Use this workflow when setting up the Credit Card Guru project for the first time on a new development environment or server.

```python
# Interactive setup with guided choices
python admin.py setup

# Expected workflow:
# 1. Choose database option (keep existing or wipe clean)
# 2. Install dependencies from requirements.txt
# 3. Create and apply database migrations
# 4. Configure Google OAuth from environment variables
# 5. Import essential system data automatically
# 6. Display next steps and available options

# Example output:
# 🚀 Starting full project setup...
# 🗃️  Database Setup Options:
# 1. Keep existing database (just add missing tables)
# 2. Completely wipe and recreate database from scratch
# Choose option (1 or 2): 1
# 🔄 Installing dependencies
# ✅ Success!
# 📥 Importing essential system data...
# ✅ Full setup complete!
```

### Example 2: Interactive Data Import Management (Secondary Use Case)
Use this for ongoing data management when you need to selectively import credit card data from multiple sources with progress tracking.

```python
# Start interactive data import session
python admin.py import-sample

# Example session:
# 📁 Available files for import:
# ==================================================
# 
# 🔧 System Files (import these first):
#   1. issuers.json
#   2. reward_types.json ✅
#   3. spending_categories.json
# 
# 💳 Card Files:
#   4. american_express.json
#   5. chase.json ✅
#   6. citi.json
#   a. Import all remaining files
#   q. Finish/Cancel
# 
# Select file(s) to import: a
# 
# 🔧 Importing system files first...
# 📄 Importing issuers.json
# ✅ issuers.json imported successfully!
# 💳 Importing card files...
# ✅ All files imported! Total: 15 files.

# Or import specific file directly
python admin.py import data/input/cards/chase.json
```

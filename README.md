# Credit Card Roadmap

A Flask web application for analyzing and recommending credit cards based on spending patterns and preferences.

## Features

- **Credit Card Database**: Comprehensive database of credit cards with reward categories, annual fees, and signup bonuses
- **Smart Recommendations**: AI-powered recommendations based on spending patterns and preferences
- **Category Management**: Flexible reward category system with aliases and mappings
- **Data Import**: Automated scraping and import of credit card data from external sources
- **User Profiles**: Save spending patterns and get personalized recommendations
- **Admin Interface**: Manage cards, categories, and issuers

## 📊 Data Management

The application includes a robust data collection and import system:

- **Automated Scraping**: Extract credit card data from financial websites
- **Timestamped Files**: All scraped data is organized with timestamps for tracking
- **Flexible Import**: Command-line and web interface import options
- **Quality Control**: Built-in validation and error handling

**📖 For detailed scraping and import instructions, see [data/README.md](data/README.md)**

## Quick Start

### Prerequisites
- Python 3.8+
- Flask and dependencies (see requirements.txt)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd creditcard-roadmap

# Install dependencies
pip install -r requirements.txt

# Initialize the database
cd flask_app
python scripts/data/reset_db.py
python scripts/data/seed_db.py

# Start the application
python run.py
```

### Access the Application
- **Web Interface**: http://127.0.0.1:5000
- **Admin Features**: Login required for data management
- **Recommendations**: Available to all users

## Technical Details

- Built with Python/Flask
- SQLAlchemy ORM for database access
- Beautiful Soup for web scraping
- Bootstrap for frontend styling

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r creditcard_roadmap/requirements.txt
   ```
3. Initialize the database:
   ```
   cd creditcard_roadmap
   flask db upgrade
   ```
4. Run the application:
   ```
   python run.py
   ```

## Project Structure

- `/app` - Main application code
  - `/models` - Database models
  - `/routes` - Route definitions
  - `/templates` - HTML templates
  - `/static` - CSS, JS, and other static files
  - `/utils` - Utility functions
- `/scripts` - Management scripts
- `/migrations` - Database migrations

## Testing

To run all tests:

```bash
python scripts/run_tests.py
```

For detailed testing documentation, see [tests/README.md](tests/README.md).

## Running Flask Scripts

Flask app scripts are organized in `flask_app/scripts/` by purpose and need to be run with the proper Python path. You have several options:

### Option 1: Interactive Menu (Recommended) 🚀
```bash
# Show numbered menu with descriptions
python scripts/run_flask_script.py

# Run script by number
python scripts/run_flask_script.py 7    # Runs data/seed_db.py
```

### Option 2: Direct Script Path
```bash
# Run specific script with category path
python scripts/run_flask_script.py data/seed_db.py
python scripts/run_flask_script.py data/import_cards.py --json data/cards.json
python scripts/run_flask_script.py test/create_test_data.py
```

### Option 3: Manual Method
```bash
# Change to flask_app directory and set PYTHONPATH
cd flask_app
PYTHONPATH=. python scripts/data/seed_db.py
```

### Script Categories
- **📁 admin/** - Administrative tools (recommendations, management)
- **📁 data/** - Database operations (seeding, importing, updating)
- **📁 scraping/** - Web scraping tools (NerdWallet data collection)
- **📁 test/** - Test data creation (users, profiles, cards)
- **📁 validate/** - Debugging and validation tools (checking data, routes, OAuth)

## Importing Credit Cards

There are several ways to import credit card data:

1. **From an HTML file**:
   ```
   python extract_card_info.py path/to/nerdwallet.html
   ```

2. **From a URL**:
   ```
   python integrate_card_data.py https://www.nerdwallet.com/best/credit-cards/
   ```

3. **From a JSON file**:
   ```
   python scripts/run_flask_script.py data/import_cards.py --json data/cards.json
   ```

When importing cards, the system will automatically handle duplicates by matching on card name and issuer. If a card with the same name and issuer already exists in the database, all its fields will be overwritten with the new values, effectively updating the card information.

## Future Enhancements

- Add more data sources beyond NerdWallet
- Implement more detailed reward calculations
- Add user accounts and authentication
- Create a more sophisticated recommendation algorithm

## Deploying to PythonAnywhere

This application includes special handling for Google OAuth when deployed to PythonAnywhere. The key changes are:

1. **WSGI File Configuration**: The `wsgi.py` file automatically detects when running on PythonAnywhere and sets the appropriate environment variables.

2. **OAuth Redirect URLs**: The auth blueprint sets the correct redirect URL based on your PythonAnywhere domain.

3. **Required Google OAuth Setup**: You must configure your Google OAuth credentials with the correct redirect URI:
   ```
   https://yourusername.pythonanywhere.com/login/google/authorized
   ```

See the [PythonAnywhere Deployment Guide](PYTHONANYWHERE_DEPLOY.md) for detailed instructions. 
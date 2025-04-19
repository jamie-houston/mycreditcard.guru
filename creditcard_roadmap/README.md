# Credit Card Roadmap

A Flask application to help users optimize their credit card strategy based on spending habits and preferences.

## Features

- Input your monthly spending across various categories
- Specify reward preferences and constraints
- Get personalized recommendations for which credit cards to apply for and when
- View detailed information about each credit card
- Calculate potential reward value based on your spending patterns

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd creditcard-roadmap
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Set up the database:
```
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Usage

1. Run the application:
```
python run.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Enter your spending information and preferences in the user profile page

4. View your personalized credit card roadmap recommendations

## Data Management

### Command-line Tools

The application includes several command-line tools for managing credit card data:

#### Update Credit Card Data

Use the `update_cards.py` script to fetch the latest credit card information from NerdWallet:

```
python scripts/update_cards.py
```

Options:
- `--force-update`: Update all cards even if no changes are detected
- `--use-proxies`: Use proxy rotation for web scraping (requires proxy configuration)
- `--limit N`: Limit the number of cards to scrape (e.g., `--limit 10`)

#### Manage Credit Cards

Use the `manage_cards.py` script to view, add, edit, or delete credit cards:

```
python scripts/manage_cards.py COMMAND [OPTIONS]
```

Commands:
- `list`: List all credit cards
  - `--issuer NAME`: Filter by issuer name
  - `--sort FIELD`: Sort by name, issuer, annual_fee, or signup_bonus_value
  - `--reverse`: Reverse the sort order
- `view ID`: View details of a specific credit card
- `add`: Add a new credit card
  - `--name NAME`: Card name (required)
  - `--issuer ISSUER`: Card issuer (required)
  - `--annual-fee FEE`: Annual fee
  - `--signup-bonus-points POINTS`: Signup bonus points
  - `--signup-bonus-value VALUE`: Dollar value of signup bonus
  - `--signup-bonus-spend AMOUNT`: Spend requirement for signup bonus
  - `--signup-bonus-time MONTHS`: Time period for signup bonus in months
  - `--rewards CATEGORY PERCENTAGE`: Add a reward category (can be used multiple times)
  - `--offers TYPE AMOUNT FREQUENCY`: Add an offer (can be used multiple times)
- `edit ID`: Edit an existing credit card
  - (Same options as `add`, plus:)
  - `--replace-rewards`: Replace all reward categories instead of adding to them
  - `--replace-offers`: Replace all offers instead of adding to them
- `delete ID`: Delete a credit card
  - `--force`: Delete without confirmation prompt

Examples:
```
# List all cards by Chase
python scripts/manage_cards.py list --issuer Chase

# View details of card with ID 1
python scripts/manage_cards.py view 1

# Add a new card
python scripts/manage_cards.py add --name "Freedom Flex" --issuer "Chase" --annual-fee 0 --signup-bonus-points 20000 --signup-bonus-value 200 --signup-bonus-spend 500 --rewards "groceries" 5 --rewards "dining" 3

# Edit a card
python scripts/manage_cards.py edit 1 --annual-fee 95 --rewards "travel" 5

# Delete a card
python scripts/manage_cards.py delete 1
```

### Adding Credit Cards Manually

To add credit card data to the system through the web interface:

1. Navigate to `/cards/new`
2. Enter the credit card details including:
   - Name and issuer
   - Annual fee
   - Reward categories (e.g., 5% on gas, 3% on groceries)
   - Card offers (e.g., travel credits, statement credits)
   - Signup bonus details

### Importing Credit Card Data

The application can import credit card data from NerdWallet using the web scraper utility:

```
python scripts/import_cards.py
```

## Development

### Project Structure

- `app/`: The main application package
  - `__init__.py`: Flask application factory
  - `models/`: Database models
  - `routes/`: Application routes
  - `templates/`: HTML templates
  - `static/`: Static assets (CSS, JavaScript)
  - `utils/`: Utility functions including the card scraper and recommendation engine
- `scripts/`: Command-line scripts for data management
- `migrations/`: Database migrations
- `config.py`: Application configuration
- `run.py`: Script to run the application

## Future Enhancements

- User accounts and saved recommendations
- More sophisticated recommendation algorithms
- Mobile app version

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
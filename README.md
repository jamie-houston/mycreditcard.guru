# Credit Card Guru

A Django-based credit card optimization platform that creates personalized roadmaps for credit card applications, cancellations, and upgrades based on spending patterns and issuer policies.


## Documentation

For detailed usage documentation, see [USAGE.md](./USAGE.md)

## Features

- **Credit Card Database**: Comprehensive database of credit cards with reward categories, signup bonuses, and offers
- **Spending Profile**: Input your monthly spending by category
- **Smart Recommendations**: Algorithm considers issuer policies (like Chase 5/24 rule)
- **Roadmap Generation**: Creates personalized action plans for credit card optimization
- **Anonymous & Logged-in Users**: Works without login, with option to save roadmaps
- **JSON Data Import**: Easy import of credit card data from JSON files

## Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone and setup virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup database**:
```bash
python manage.py migrate
```

3. **Import initial data**:

**Option A: Use the setup script (recommended)**:
```bash
python setup_data.py
```

**Option B: Manual import**:
```bash
# Import basic system data
python manage.py loaddata data/input/system/spending_categories.json
python manage.py loaddata data/input/system/issuers.json
python manage.py loaddata data/input/system/reward_types.json

# Import credit cards from all available files
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/american_express.json
# ... repeat for other card files

# Import credit types (for offers/benefits in roadmap preferences)
python manage.py import_credit_types
```

4. **Create admin user** (optional):
```bash
python manage.py createsuperuser
```

5. **Run the development server**:
```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to see the application.

## Project Structure

```
creditcard_guru/
├── cards/              # Credit card models and data
├── roadmaps/           # Recommendation engine
├── users/              # User management
├── creditcard_guru/    # Django settings
└── sample_cards.json   # Sample data
```

## Data Models

### Core Models
- **Issuer**: Credit card companies (Chase, Amex, etc.) with policies
- **CreditCard**: Individual credit cards with fees, bonuses
- **RewardCategory**: Earning rates by spending category
- **UserSpendingProfile**: User spending patterns
- **Roadmap**: Generated recommendations

### JSON Import Format

```json
{
  "issuers": [
    {"name": "Chase", "max_cards_per_period": 5, "period_months": 24}
  ],
  "reward_types": [
    {"name": "Points"}
  ],
  "spending_categories": [
    {"name": "Travel"}
  ],
  "credit_cards": [
    {
      "name": "Sapphire Preferred",
      "issuer": "Chase",
      "annual_fee": 95,
      "signup_bonus_amount": 60000,
      "signup_bonus_type": "Points",
      "primary_reward_type": "Points",
      "verified": true,
      "reward_categories": [
        {"category": "Travel", "reward_rate": 2.0, "reward_type": "Points"}
      ]
    }
  ]
}
```

## Development

### Management Commands

- `python manage.py import_cards <file.json>` - Import credit card data
- `python manage.py import_credit_types` - Import credit types (offers/benefits) from card files
- `python manage.py shell_plus` - Enhanced Django shell

### Admin Interface

Access the admin at http://127.0.0.1:8000/admin/ to manage:
- Credit cards and issuers
- Reward categories and offers
- User spending profiles
- Roadmaps and recommendations

## Next Steps

1. **Recommendation Engine**: Implement the core algorithm considering:
   - Issuer policies (5/24 rule, etc.)
   - Reward optimization
   - Annual fee vs. benefits analysis

2. **Frontend**: Build user interface for:
   - Spending input forms
   - Card filtering and selection
   - Roadmap visualization

3. **API Endpoints**: Create REST API for:
   - Card search and filtering
   - Roadmap generation
   - User profile management

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Task Queue**: Celery + Redis
- **Admin**: Django Admin
- **API**: REST API with pagination
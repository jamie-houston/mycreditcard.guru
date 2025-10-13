# Credit Card Guru

A Django-based credit card optimization platform that generates personalized roadmaps for credit card applications, cancellations, and upgrades. The system analyzes user spending patterns against issuer policies (like Chase's 5/24 rule) to recommend optimal credit card strategies for maximizing rewards.

## Quick Start

### First Time Setup

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run the interactive management script
python manage_project.py

# 3. Select option 3: Reset database (creates DB + imports all data)
# 4. Select option 1: Run development server
```

Visit **http://localhost:8000/**

### Running the Server

```bash
# Option A: Interactive script (recommended)
python manage_project.py
# Select option 1

# Option B: Direct command
python manage.py runserver

# Option C: Debug in VS Code/Cursor
# Press F5
```

## Features

- **Portfolio Optimization**: Recommends optimal card combinations rather than individual cards
- **Issuer Policy Engine**: Respects rules like Chase 5/24, application velocity limits
- **Anonymous Support**: Full functionality without registration using session tracking
- **Spending Analysis**: Matches card benefits to user spending patterns
- **Smart Recommendations**: Anti-overlap logic prevents double-counting rewards
- **Roadmap Generation**: Creates actionable credit card application/cancellation plans

## Interactive Management Script

The `manage_project.py` script provides a menu-driven interface for all development tasks:

```
1. Run development server         → Start Django at http://127.0.0.1:8000/
2. Run tests                       → Run Django test suite (all or specific)
3. Reset database                  → Delete and recreate database with fresh data
4. Migrate database               → Run/create database migrations
5. Import credit card data        → Import cards, issuers, categories
6. Show database info             → View counts of data in database
7. Manage superuser               → Create/modify admin users
8. Open Django shell              → Interactive Django shell
9. Exit                           → Quit the script
```

## Project Architecture

### Django Apps

- **`cards/`** - Credit card database, user profiles, card ownership tracking
- **`roadmaps/`** - Recommendation engine and portfolio optimization
- **`users/`** - User management with anonymous session support

### Key Models

- `CreditCard` - Card details with JSON metadata for flexible attributes
- `Issuer` - Card issuers with application policies (5/24, velocity limits)
- `SpendingCategory` - Hierarchical spending categories
- `UserSpendingProfile` - User spending patterns (authenticated or session-based)
- `Roadmap` - Generated recommendations with portfolio calculations
- `UserCard` - Detailed card ownership history with open/close dates

### Recommendation Engine

The core engine (`roadmaps/recommendation_engine.py`, 1,923 lines) implements:

- Portfolio-first optimization (not simple card suggestions)
- Anti-overlap logic to prevent reward double-counting
- Issuer policy compliance checking
- Spending efficiency scoring
- Greedy algorithm for optimal card selection
- Scenario analysis (keeping profitable cards vs. full optimization)

## Documentation

- **[RUNNING.md](RUNNING.md)** - Comprehensive setup and troubleshooting guide
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference for common tasks
- **[CLAUDE.md](CLAUDE.md)** - Project overview and architecture for AI assistants
- **[PRD.md](PRD.md)** - Product requirements and specifications
- **[docs/](docs/)** - Additional documentation (deployment, testing)

## Development

### Prerequisites

- Python 3.8+
- Virtual environment activated
- `.env` file configured (see `.env.example`)

### Common Commands

```bash
# Import all data (fresh database)
python manage_project.py  # Select option 5 → 1

# Import specific issuer
python manage.py import_cards data/input/cards/chase.json

# Run tests
python manage.py test

# Create superuser for admin access
python manage.py createsuperuser

# Access admin panel
http://localhost:8000/admin/
```

### Management Commands

- `import_cards <file.json>` - Import credit card data (handles all file types)
- `import_credit_types` - Import benefit/offer types for preferences
- `import_spending_credits` - Import spending credit types (lounge access, etc.)

### API Endpoints

- `/api/cards/` - Card search, user profiles, quick recommendations
- `/api/roadmaps/` - Roadmap CRUD, generation, portfolio statistics
- `/api/users/` - Authentication status, profile management

All endpoints support anonymous users via session-based tracking.

## Data Import

### JSON Data Structure

Credit card data is organized in `/data/input/`:

- `/system/` - Core data (categories, issuers, reward types)
- `/cards/` - Card data by issuer (chase.json, american_express.json, etc.)

The `import_cards` command automatically detects file type and imports appropriately.

### Import Options

```bash
# Option 1: Use interactive script (easiest)
python manage_project.py  # Select 5 → 1

# Option 2: Use setup script
python setup_data.py

# Option 3: Manual import
python manage.py import_cards data/input/system/issuers.json
python manage.py import_cards data/input/system/spending_categories.json
python manage.py import_cards data/input/system/reward_types.json
python manage.py import_spending_credits
python manage.py import_cards data/input/cards/*.json
python manage.py import_credit_types
```

## Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test cards
python manage.py test roadmaps

# Use interactive script
python manage_project.py  # Select option 2
```

## Technology Stack

- **Backend**: Django 5.1, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production-ready)
- **Authentication**: django-allauth (email + Google OAuth)
- **Frontend**: Django templates with modern CSS
- **API**: RESTful with anonymous user support

## Deployment

The application is production-ready and currently hosted on PythonAnywhere. See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for deployment instructions.

## Key Design Decisions

1. **Portfolio-First Approach** - Optimizes entire card portfolios, not individual suggestions
2. **Anonymous Functionality** - Full features without registration using session keys
3. **Hierarchical Categories** - Spending categories support parent/child relationships
4. **JSON Flexibility** - Card metadata in JSON fields for diverse card features
5. **Issuer Policy Engine** - Built-in support for complex issuer rules

## License

Proprietary - All rights reserved

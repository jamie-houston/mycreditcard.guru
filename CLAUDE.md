# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
cd flask_app
python run.py
```

### Testing
```bash
# Run all tests (from project root)
python flask_app/run_tests.py -y

# Run tests with coverage
python flask_app/run_tests.py -c -y

# Run Flask app tests only
python flask_app/run_tests.py --flask-only -y

# Tests use pytest with configuration in flask_app/pytest.ini
cd flask_app && python -m pytest tests/ -v
```

### Database Management
```bash
# From project root, use the Flask script runner:
python scripts/run_flask_script.py data/reset_db.py           # Reset database
python scripts/run_flask_script.py data/seed_db.py            # Seed with sample data
python scripts/run_flask_script.py data/seed_issuer_policies.py  # Seed issuer policies (Chase 5/24, etc.)
python scripts/run_flask_script.py data/import_cards.py --json path/to/cards.json
```

### Web Scraping and Data Import
```bash
python scripts/run_flask_script.py scraping/scrape_nerdwallet.py
python scripts/run_flask_script.py guided_scraping.py  # Interactive workflow
```

## Architecture Overview

### Core Application Structure
- **Flask App Factory Pattern**: App created via `create_app()` in `app/__init__.py`
- **Blueprint Organization**: Features split into blueprints (`auth`, `recommendations`, `admin`, `roadmap`, etc.)
- **SQLAlchemy 2.x**: Modern ORM with relationship-based queries
- **Dual User System**: Supports both authenticated users and anonymous sessions

### Key Models and Relationships
- **CreditCard**: Core entity with reward rates, annual fees, signup bonuses
- **UserCard**: Junction table tracking user's owned cards with acquisition dates, bonus status
- **IssuerPolicy**: Configurable application rules (Chase 5/24, Amex 2/90, etc.)
- **Category**: Reward categories (dining, travel, gas, etc.) with flexible aliasing system
- **CreditCardReward**: Junction table linking cards to reward categories with rates/limits
- **UserProfile**: Spending patterns by category, constraints (max annual fee, card count)
- **RecommendationEngine**: Calculates card value based on spending patterns and reward rates
- **RoadmapEngine**: Advanced engine for portfolio optimization and application timing

### Recommendation Engine Logic
- Monthly spending × reward rate × reward_value_multiplier = card value
- Respects spending limits per category (excess goes to "other" rate)
- Filters by max annual fee constraint and maximum number of cards
- Prioritizes cards with highest reward rates for user's spending categories
- Supports both travel and cash back reward types

### Phase 2: Roadmap Engine Features
- **Portfolio Management**: Track owned cards with acquisition dates and bonus status
- **Current Usage Roadmap**: Shows which card to use for each spending category
- **Application Strategy**: Recommends when to apply for new cards considering issuer policies
- **Cancellation Recommendations**: Identifies cards with poor value proposition
- **Bonus Optimization**: Tracks signup bonus deadlines and spending requirements
- **Policy Compliance**: Respects issuer rules like Chase 5/24, Amex 2/90, etc.
- **Timeline Generation**: Creates optimal application schedule based on spending velocity

### Data Flow
1. **Web Scraping**: NerdWallet data → timestamped JSON files in `data/output/`
2. **Import Process**: JSON → database via `import_cards.py` with reward category mapping
3. **Recommendation**: User profile + card database → RecommendationEngine → ranked suggestions

## Key Configuration

### Flask Configuration
- **Development**: SQLite database in `flask_app/instance/`
- **Testing**: Separate test database (`test_creditcard_roadmap.db`)
- **Authentication**: Google OAuth via Flask-Dance
- **CSRF Protection**: Enabled via Flask-WTF

### Database
- **ORM**: SQLAlchemy 2.x with relationship loading
- **Migrations**: Alembic in `/migrations` directory
- **Test Safety**: TestingConfig enforces separate test database

## Important Patterns

### Error Handling
- Early returns for error conditions (guard clauses)
- Proper error logging via `app.logger`
- User-friendly error messages in templates

### Script Execution
Use `scripts/run_flask_script.py` for all Flask app scripts to ensure proper Python path:
```bash
python scripts/run_flask_script.py category/script_name.py [args]
```

### Template System
- **Base Template**: `templates/base.html` with Bootstrap styling
- **Context Processors**: Utility functions available in all templates
- **Custom Filters**: JSON parsing, date formatting

### Data Validation
- Marshmallow schemas for serialization/validation
- WTForms for form handling
- Input sanitization for scraped data

## Scraping and Import Rules

### Data Sources
- Primary: NerdWallet HTML tables → JSON → database
- All scraped data timestamped in `data/output/YYYYMMDDHHMM_source_cards.json`
- Duplicate handling: Match on card name + issuer, update all fields

### Reward Category Mapping
- Flexible aliasing system in Category model
- "dining" category includes restaurants, food delivery
- "travel" includes airlines, hotels, booking sites
- Default "other" rate for unmatched spending

### Quality Control
- Built-in validation for required fields
- Error handling for malformed scraped data
- Rollback on import failures
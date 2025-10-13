# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Credit Card Guru is a Django-based credit card optimization platform that generates personalized roadmaps for credit card applications, cancellations, and upgrades. The system analyzes user spending patterns against issuer policies (like Chase's 5/24 rule) to recommend optimal credit card strategies for maximizing rewards.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment with Python 3.8+
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database and import all data
python setup_data.py

# Run development server
python manage.py runserver
```

### Data Management
```bash
# Import credit card data from JSON files
python manage.py import_cards

# Import benefit/credit types
python manage.py import_credit_types

# Run database migrations
python manage.py migrate
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test cards
python manage.py test roadmaps
```

## Core Architecture

### Django App Structure

**`cards/`** - Credit card database and user profiles
- Manages credit cards, issuers, reward categories, spending profiles
- Handles user card ownership tracking with detailed history
- Provides search/filtering APIs with anonymous user support

**`roadmaps/`** - Recommendation engine and roadmap generation
- Contains the core `RecommendationEngine` class (1,923 lines)
- Generates portfolio-optimized recommendations rather than simple suggestions
- Implements sophisticated algorithms for spending allocation optimization

**`users/`** - User management with anonymous support
- Extended user profiles and preferences
- Session-based functionality for unregistered users
- Integration with django-allauth for email/Google OAuth authentication

### Key Data Models

**Core Relationships:**
- `SpendingCategory` supports hierarchical parent/child relationships
- `UserCard` tracks detailed ownership history with open/close dates
- `CreditCard` uses JSON metadata fields for flexible attributes
- `UserSpendingProfile` supports both authenticated users and anonymous sessions

**Portfolio Optimization Models:**
- `Roadmap` contains recommendation filters and parameters
- `RoadmapRecommendation` tracks individual card actions (apply/keep/cancel/upgrade)
- `RoadmapCalculation` stores calculated portfolio values with JSON breakdowns

### Recommendation Engine Architecture

The recommendation engine (`roadmaps/recommendation_engine.py`) implements sophisticated portfolio optimization:

- **Anti-overlap Logic**: Prevents double-counting rewards across multiple cards
- **Issuer Policy Compliance**: Respects rules like Chase 5/24 and application velocity limits
- **Spending Efficiency Scoring**: Matches card benefits to user spending patterns
- **Greedy Optimization**: Selects optimal card combinations from eligible candidates
- **Scenario Analysis**: Balances keeping profitable cards vs. full portfolio optimization

### API Structure

**REST Framework Design:**
- `/api/cards/` - Card search, user profiles, recommendations preview
- `/api/roadmaps/` - Roadmap CRUD, generation, and portfolio statistics
- `/api/users/` - Authentication status, profile management, card ownership

**Anonymous User Support:**
- All endpoints use `AllowAny` permissions to support unregistered users
- Session-based tracking for anonymous spending profiles and roadmaps
- UUID-based public sharing for spending profiles

### Data Import System

**JSON Data Structure:**
- Card data organized by issuer in `/data/input/cards/`
- System data (categories, issuers) in `/data/input/system/`
- Flexible JSON schema with signup bonuses, reward categories, and credits

**Import Commands:**
- `setup_data.py` - Automated full setup for fresh installations
- Management commands for incremental updates and specific data types

## Development Patterns

### Frontend Integration
- Django templates with server-side rendering
- Modern CSS with Inter typography and gradient backgrounds
- REST API endpoints designed for potential SPA migration

### Database Strategy
- SQLite for development, PostgreSQL production-ready
- Extensive use of select_related/prefetch_related for performance
- JSON fields for flexible card attributes without schema changes

### Error Handling
- Graceful degradation between anonymous and authenticated user workflows
- Comprehensive validation in serializers and recommendation engine
- Session fallback patterns for unauthenticated operations

## Key Technical Decisions

1. **Portfolio-First Approach**: Recommendations optimize entire card portfolios rather than suggesting individual cards
2. **Anonymous Functionality**: Full platform features available without registration using session keys
3. **Hierarchical Categories**: Spending categories support parent/child relationships for flexible categorization
4. **JSON Flexibility**: Credit card metadata stored in JSON fields to accommodate diverse card features
5. **Issuer Policy Engine**: Built-in support for complex issuer rules and application restrictions

## Documentation Guidelines

**Important**: When making code changes, always follow the documentation guidelines in `.cursor/rules/documentation.mdc`.

### Key Documentation Rules:
- **Before changes**: Review CLAUDE.md (this file) and relevant documentation
- **After changes**: Update documentation to reflect new functionality
- **Architecture changes**: Update CLAUDE.md
- **New workflows**: Update RUNNING.md and QUICKSTART.md
- **Import changes**: Update docs/CARD_IMPORT_GUIDE.md

### Documentation Structure:
- **CLAUDE.md** (this file) - Project overview for AI assistants
- **README.md** - Main project documentation
- **RUNNING.md** - Setup and troubleshooting
- **QUICKSTART.md** - Quick reference guide
- **docs/** - Detailed guides (imports, deployment, testing)

**See `.cursor/rules/documentation.mdc` for complete guidelines on when and how to update documentation.**
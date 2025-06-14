# Database Seeding Scripts

This directory contains modular database seeding scripts for the Credit Card Roadmap application.

## Overview

The seeding system has been reorganized into individual, modular scripts that can be run independently or together via the main reset script.

## Scripts

### `reset_db.py` - Main Reset & Seed Script
**Purpose**: Drops all tables, recreates them, and seeds with sample data.

**Usage**:
```bash
python reset_db.py
```

**What it does**:
1. 🗑️ Drops all existing database tables
2. 🏗️ Creates all tables from current models
3. 📊 Seeds sample data in proper dependency order:
   - Categories (needed by credit cards)
   - Card issuers (needed by credit cards)
   - Credit cards (with reward relationships)
   - ~~User profiles~~ (temporarily disabled due to model issues)

### Individual Seed Scripts

Each model has its own seed script that can be run independently:

#### `seed_categories.py`
- Seeds 23+ spending/reward categories
- Includes aliases for flexible matching
- Updates existing categories with new data
- **Usage**: `python seed_categories.py`

#### `seed_issuers.py`
- Seeds 15+ major credit card issuers
- Skips existing issuers to avoid duplicates
- **Usage**: `python seed_issuers.py`

#### `seed_credit_cards.py`
- Seeds 8+ realistic sample credit cards
- Includes popular cards from major issuers
- Creates proper reward category relationships
- Handles spending limits and bonus categories
- **Usage**: `python seed_credit_cards.py`

#### `seed_profiles.py` *(Currently Disabled)*
- Would seed sample user profiles for testing
- Temporarily disabled due to model relationship issues
- **Usage**: `python seed_profiles.py` (when fixed)

## Sample Data Included

### Credit Cards
- **Chase Cash Rewards Card** - Basic cash back with category bonuses
- **Chase Sapphire Preferred** - Travel rewards with transfer partners
- **American Express Platinum** - Premium travel card with high annual fee
- **American Express Blue Cash Preferred** - Grocery/streaming bonuses
- **Capital One Venture Rewards** - Flat-rate travel rewards
- **Citi Double Cash** - Simple 2% on everything
- **Discover it Cash Back** - Rotating categories with cashback match
- **Citi Custom Cash** - Choose your 5% category

### Categories
Comprehensive list including: dining, travel, groceries, gas, entertainment, shopping, streaming, drugstores, and more.

### Issuers
Major banks and credit unions: Chase, American Express, Capital One, Citi, Discover, Bank of America, Wells Fargo, U.S. Bank, and others.

## Development Notes

- All scripts use proper Flask app context
- Scripts are idempotent (safe to run multiple times)
- Existing data is preserved where possible
- Dependencies are handled in correct order
- Each script provides clear feedback with emojis 🎉

## Troubleshooting

If you encounter import errors, make sure you're running the scripts from the correct directory:
```bash
cd flask_app/scripts/data
python reset_db.py
```

The scripts automatically add the Flask app directory to the Python path.

---

*"Why did the database go to therapy? It had too many relationship issues!" 😄* 
# Credit Card Import System - Complete Guide

## Overview

The credit card import system uses the `import_cards` management command to load credit card data from JSON files. **Only cards marked with `"verified": true`** are imported into the database.

## Keeping Bonuses & Fees Current (import_external_cards)

Signup bonus offers and annual fees churn constantly; reward categories and credits don't.
The `import_external_cards` command refreshes only the churning fields from the
[andenacitelli community API](https://github.com/andenacitelli/credit-card-bonuses-api):

```bash
python manage.py import_external_cards            # fetch, update JSON, re-import to DB
python manage.py import_external_cards --dry-run  # preview changes only
python manage.py import_external_cards --file data/external/andenacitelli.json  # offline
```

How it works:
- Fetches the API export (cached to `data/external/andenacitelli.json` as a fallback).
- Matches API cards to entries in `data/input/cards/*.json` by normalized name + issuer;
  renamed cards are pinned in `data/input/overrides/external_card_map.json`.
- Updates `signup_bonus` (amount, spending requirement, time limit), `annual_fee`,
  `discontinued`, and first-year fee waivers **in the JSON files** — they remain the
  source of truth, and `git diff data/input/cards/` shows exactly what offers changed.
- Re-imports changed files via `import_cards` (so only `verified: true` cards hit the DB).
- Reports API cards missing from the catalog (new product launches) and never clobbers a
  curated bonus when the API shows no current offer — it warns instead.

It's idempotent and safe to run monthly (PythonAnywhere scheduled task after deploy).
Curated detail — reward categories, credits, `reward_value_multiplier`, referral URLs —
is never touched.

## Key Import Rule

**🔑 CRITICAL**: The import command **only imports cards with `"verified": true`** in the JSON. Cards without this flag or with `"verified": false` are skipped.

```json
{
  "name": "Card Name",
  "issuer": "Chase",
  "verified": true,    // ← This must be true to import!
  "annual_fee": 95,
  ...
}
```

## Current Card Data Status

As of the latest data check, here's what will actually be imported:

| Issuer File | Total Cards | Verified (Will Import) |
|-------------|-------------|------------------------|
| chase.json | 36 cards | **12 cards** ✓ |
| american_express.json | 31 cards | **3 cards** ✓ |
| capital_one.json | 10 cards | **5 cards** ✓ |
| wells_fargo.json | 9 cards | **3 cards** ✓ |
| citi.json | 10 cards | **1 card** ✓ |
| bank_of_america.json | 13 cards | **0 cards** ✗ |
| barclays.json | 21 cards | **0 cards** ✗ |
| us_bank.json | 12 cards | **0 cards** ✗ |
| first.json | 7 cards | **0 cards** ✗ |
| fnbo.json | 4 cards | **0 cards** ✗ |
| penfed.json | 3 cards | **0 cards** ✗ |
| synchrony.json | 2 cards | **0 cards** ✗ |
| brex.json | 1 card | **0 cards** ✗ |
| discover.json | 1 card | **0 cards** ✗ |
| pnc.json | 1 card | **0 cards** ✗ |
| web_bank.json | 1 card | **0 cards** ✗ |

**Total: 162 cards in files, 24 verified cards will be imported**

## How the Import Command Works

### File Detection Logic

The `import_cards` command automatically detects file type by filename:

```python
# Specific system files (auto-detected)
issuers.json           → Imports issuer data
reward_types.json      → Imports reward types (Points, Miles, Cashback)
spending_categories.json → Imports spending categories

# Credit card files (auto-detected)
chase.json, american_express.json, citi.json, capital_one.json
→ Imports credit cards from these files

# Generic detection
*.json with array of cards → Imports as credit cards
*.json with object         → Legacy combined format
```

### Import Process

1. **File is loaded** and JSON is parsed
2. **Filename is checked** to determine type
3. **For card files**: Loops through each card
4. **Verification check**: Skips any card with `verified != true`
5. **Issuer lookup**: Finds the issuer in the database
6. **Card creation/update**:
   - If card exists (by name + issuer): Updates all fields
   - If card is new: Creates new card with auto-generated slug
7. **Related data import**: Imports reward categories and card credits

### What Gets Imported

For each verified card, the following is imported:

```json
{
  "name": "Card Name",                    // Required
  "issuer": "Chase",                      // Required (must exist in DB)
  "verified": true,                       // Required to import!
  "annual_fee": 95,                       // Default: 0
  "card_type": "personal",                // Default: "personal" (or "business")
  "url": "https://...",                   // Card application URL

  // Signup Bonus (two formats supported)
  "signup_bonus": {
    "bonus_amount": 60000,
    "spending_requirement": 4000,
    "time_limit_months": 3,
    "bonus_type": "Points"
  },
  // OR legacy format:
  "signup_bonus_amount": 60000,
  "signup_bonus_requirement": "$4000 in 3 months",

  // Rewards
  "primary_reward_type": "Points",        // Required (Points/Miles/Cashback)
  "reward_value_multiplier": 0.01,        // Point value (e.g., 0.02 = 2¢/point)

  // Earning Categories
  "reward_categories": [
    {
      "category": "travel",               // Must match SpendingCategory slug
      "rate": 3.0,                        // 3x points
      "reward_type": "Points",
      "annual_cap": 0,                    // 0 = no cap
      "description": "Travel purchased through Chase"
    }
  ],

  // Card Benefits/Credits
  "credits": [
    {
      "credit_type": "travel",
      "amount": 300,
      "frequency": "annual",
      "description": "$300 annual travel credit"
    }
  ],

  // Additional metadata
  "metadata": {
    "discontinued": false,
    "notes": "Additional info"
  }
}
```

## Import Commands

### Using the Interactive Script (Recommended)

```bash
python manage_project.py
# Select: 5 (Import credit card data)
# Then choose:
#   1 - Import ALL data (system + all cards)
#   2 - Import system data only
#   3 - Import all credit cards only
#   4 - Import specific issuer
```

### Using Setup Script

```bash
python setup_data.py
```

This automatically imports:
1. System data (issuers, categories, reward types)
2. All credit card files (*.json in data/input/cards/)
3. Spending credits
4. Credit types (benefits/offers)

### Manual Import Commands

```bash
# Import system data first (required)
python manage.py import_cards data/input/system/issuers.json
python manage.py import_cards data/input/system/spending_categories.json
python manage.py import_cards data/input/system/reward_types.json
python manage.py import_spending_credits

# Import specific issuer
python manage.py import_cards data/input/cards/chase.json

# Import all cards (only verified ones)
for file in data/input/cards/*.json; do
  python manage.py import_cards "$file"
done
```

## Verifying Cards to Import More Cards

To add more cards to the database, you need to set `"verified": true` in the JSON files:

### Example: Enabling a Card for Import

**Before (card will be skipped):**
```json
{
  "name": "Bank of America Premium Rewards",
  "issuer": "Bank of America",
  "verified": false,    // ← Card will be skipped!
  "annual_fee": 95,
  ...
}
```

**After (card will be imported):**
```json
{
  "name": "Bank of America Premium Rewards",
  "issuer": "Bank of America",
  "verified": true,     // ← Card will now import!
  "annual_fee": 95,
  ...
}
```

### Why the Verified Flag?

The `verified` flag ensures:
- **Data Quality**: Only cards with complete/accurate data are imported
- **Testing**: Unverified cards can stay in files without affecting production
- **Gradual Rollout**: Cards can be prepared and verified before going live
- **Data Integrity**: Prevents importing incomplete or placeholder cards

## Import Order & Dependencies

**Important**: Import in this order to avoid errors:

1. **System Data First** (issuers, categories, reward types)
   - Cards reference these, so they must exist first

2. **Spending Credits** (optional benefits like lounge access)
   - Card credits reference these

3. **Credit Cards** (the actual cards)
   - References issuers, reward types, categories

4. **Credit Types** (benefit preferences)
   - Extracted from all imported cards

### Full Import Command Sequence

```bash
# 1. System foundation
python manage.py import_cards data/input/system/issuers.json
python manage.py import_cards data/input/system/spending_categories.json
python manage.py import_cards data/input/system/reward_types.json

# 2. Spending credits (for card benefits)
python manage.py import_spending_credits

# 3. All credit cards
python manage.py import_cards data/input/cards/american_express.json
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/capital_one.json
python manage.py import_cards data/input/cards/wells_fargo.json
python manage.py import_cards data/input/cards/citi.json
# ... (continue for other issuers)
```

## Checking Import Results

### After Import, Verify Data

```bash
# Option 1: Interactive script
python manage_project.py
# Select: 6 (Show database info)

# Option 2: Django shell
python manage.py shell
```

In the shell:
```python
from cards.models import CreditCard, Issuer

# Count total cards
print(f"Total cards: {CreditCard.objects.count()}")

# Cards by issuer
for issuer in Issuer.objects.all():
    count = CreditCard.objects.filter(issuer=issuer).count()
    print(f"{issuer.name}: {count} cards")

# Check specific card
card = CreditCard.objects.filter(name__icontains="Sapphire").first()
if card:
    print(f"\nCard: {card.name}")
    print(f"Annual Fee: ${card.annual_fee}")
    print(f"Signup Bonus: {card.signup_bonus_amount} {card.signup_bonus_type}")
    print(f"Reward Categories: {card.reward_categories.count()}")
```

### Expected Results After Full Import

With current verified cards:
```
Credit Cards: 24 (only verified cards)
Issuers: 16
Spending Categories: 29
Reward Categories: ~60-100 (varies by card)
Credit Types: ~15-20
```

## Troubleshooting

### "Issuer not found" Error

```
Error: Issuer "Chase" not found
```

**Solution**: Import issuers first:
```bash
python manage.py import_cards data/input/system/issuers.json
```

### "Category not found" Warning

```
Warning: Spending category 'online_shopping' not found
```

**Solution**: Import spending categories:
```bash
python manage.py import_cards data/input/system/spending_categories.json
```

### "Skipping unverified card" Messages

```
Skipping unverified card: Barclays Arrival Premier
```

This is **normal**. Cards without `"verified": true` are intentionally skipped. To import them:
1. Edit the JSON file
2. Set `"verified": true` for desired cards
3. Re-run import command

### No Cards Imported from File

**Check**:
1. Are cards in the file marked with `"verified": true`?
2. Does the issuer exist in the database?
3. Is the file format correct (array of card objects)?

```bash
# Check verified count in file
jq '[.[] | select(.verified == true)] | length' data/input/cards/chase.json
```

### Card Already Exists

The import command **updates** existing cards by default. If a card with the same name and issuer exists, it will be updated with new data.

To see what changed:
```bash
# Before import
python manage.py shell -c "from cards.models import CreditCard; print(CreditCard.objects.get(name='Sapphire Preferred', issuer__name='Chase').annual_fee)"

# After import
# (check again)
```

## Adding New Cards

To add a completely new card:

1. **Add to appropriate issuer file** (e.g., `data/input/cards/chase.json`)
2. **Set `"verified": true`** to enable import
3. **Ensure issuer exists** in `data/input/system/issuers.json`
4. **Match category slugs** to existing categories
5. **Run import** command

Example new card:
```json
{
  "name": "My New Card",
  "issuer": "Chase",
  "verified": true,
  "annual_fee": 0,
  "signup_bonus": {
    "bonus_amount": 20000,
    "spending_requirement": 500,
    "time_limit_months": 3
  },
  "primary_reward_type": "Points",
  "reward_value_multiplier": 0.01,
  "card_type": "personal",
  "url": "https://example.com/apply",
  "reward_categories": [
    {
      "category": "all",
      "rate": 1.0,
      "reward_type": "Points"
    }
  ],
  "credits": [],
  "metadata": {}
}
```

Then import:
```bash
python manage.py import_cards data/input/cards/chase.json
```

## File Locations

```
data/input/
├── system/
│   ├── issuers.json               # Card issuers (Chase, Amex, etc.)
│   ├── spending_categories.json   # Spending categories (travel, dining, etc.)
│   └── reward_types.json          # Reward types (Points, Miles, Cashback)
└── cards/
    ├── american_express.json      # 3 verified cards
    ├── bank_of_america.json       # 0 verified cards
    ├── barclays.json              # 0 verified cards
    ├── capital_one.json           # 5 verified cards
    ├── chase.json                 # 12 verified cards
    ├── citi.json                  # 1 verified card
    ├── wells_fargo.json           # 3 verified cards
    └── ... (other issuers)
```

## Summary

**Key Points to Remember:**

1. ✅ Only cards with `"verified": true` are imported
2. ✅ Import system data (issuers, categories) before cards
3. ✅ Currently 24/162 cards are verified and will import
4. ✅ Use `python manage_project.py` for easiest import process
5. ✅ Cards are updated if they already exist (by name + issuer)
6. ✅ Check `manage_project.py` option 6 to verify imports worked

**To import more cards:** Edit the JSON files and set `"verified": true` for the cards you want to include.

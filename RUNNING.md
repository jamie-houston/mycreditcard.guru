# Running Credit Card Guru Locally

## Quick Start

### 1. Setup (First Time Only)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the interactive management script
python manage_project.py

# Select option 3: Reset database
# This will:
#   - Create a fresh database
#   - Prompt you to create a superuser (recommended)
#   - Import all data automatically
```

### 2. Run the Server

```bash
# Option A: Using the management script
python manage_project.py
# Select option 1: Run development server

# Option B: Using manage.py directly
python manage.py runserver

# Option C: Debug in Cursor/VS Code
# Press F5 and select "Django: Run Server"
```

Then visit: **http://localhost:8000/**

## Interactive Management Script

The `manage_project.py` script provides a menu-driven interface for all common tasks:

```bash
python manage_project.py
```

### Available Options:

```
1. Run development server         → Start Django at http://127.0.0.1:8000/
2. Run tests                       → Run Django test suite
3. Reset database                  → Delete and recreate with fresh data
4. Migrate database               → Run database migrations
5. Import credit card data        → Import cards, issuers, categories
6. Show database info             → View database statistics
7. Manage superuser               → Create/modify admin users
8. Open Django shell              → Interactive Django shell
9. Exit                           → Quit the script
```

## Common Scenarios

### Import All Credit Card Data

If your database is missing card data:

```bash
python manage_project.py
# Select: 5 → 1 (Import ALL data)
```

This will import:
- ✓ Spending categories (29 categories)
- ✓ Issuers (16 issuers)
- ✓ Reward types (Points, Miles, Cashback, etc.)
- ✓ Spending credits (Airport lounge, streaming services, etc.)
- ✓ Credit cards from all issuers (~100+ cards)
- ✓ Credit types (benefits and offers)

### Import Specific Issuer

To import cards from just one issuer (e.g., Chase, Amex):

```bash
python manage_project.py
# Select: 5 → 4 (Import specific issuer)
# Choose from the numbered list
```

### Run Tests

```bash
python manage_project.py
# Select: 2 (Run tests)
# Then choose:
#   1. All tests
#   2. Specific app (cards/roadmaps/users)
#   3. Specific test file
```

### Fresh Start (Reset Everything)

To completely reset and start over:

```bash
python manage_project.py
# Select: 3 (Reset database)
# Type: RESET
# Follow prompts to create superuser
# All data will be imported automatically
```

### Access Admin Panel

1. Create a superuser:
   ```bash
   python manage_project.py
   # Select: 7 → 1 (Create superuser)
   ```

2. Run the server and visit:
   **http://localhost:8000/admin/**

## Manual Commands

If you prefer the command line:

```bash
# Import system data
python manage.py import_cards data/input/system/issuers.json
python manage.py import_cards data/input/system/spending_categories.json
python manage.py import_cards data/input/system/reward_types.json

# Import spending credits (for card benefits)
python manage.py import_spending_credits

# Import card data
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/american_express.json
# ... etc for other issuers

# Import credit types (benefits/offers for preferences)
python manage.py import_credit_types

# Or use the setup script to import everything
python setup_data.py

# Run server
python manage.py runserver

# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser
```

## Debugging in Cursor/VS Code

Press **F5** to start debugging. Available configurations:

- **Django: Run Server** - Normal server with auto-reload
- **Django: Run Server (Debug)** - Server with `--noreload` (better for breakpoints)
- **Django: Run Tests** - Run full test suite
- **Django: Shell** - Interactive Django shell
- **Django: Migrate** - Run migrations
- **Django: Create Superuser** - Create admin user

Set breakpoints in your code and they'll be hit when you interact with the app.

## Verifying Your Setup

Check that data was imported correctly:

```bash
python manage_project.py
# Select: 6 (Show database info)
```

You should see something like:
```
Credit Cards: 100+
Issuers: 16
Spending Categories: 29
Users: 1+
Roadmaps: 0
```

## Troubleshooting

### "No credit cards found"

Your database needs data. Run:
```bash
python manage_project.py
# Select: 5 → 1 (Import ALL data)
```

### "Virtual environment not activated"

```bash
source venv/bin/activate
```

### Port 8000 already in use

```bash
# Kill the existing server
lsof -ti:8000 | xargs kill -9

# Or use a different port
python manage.py runserver 8001
```

### Import errors

If imports fail:
1. Make sure migrations are up to date: `python manage.py migrate`
2. Check that data files exist: `ls data/input/cards/`
3. Try resetting the database (option 3 in management script)

### Server runs but pages error

This was likely the Google OAuth issue we fixed. If you still see errors:

```bash
# Recreate the OAuth app
python manage.py shell
```

Then in the shell:
```python
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
import os

site = Site.objects.get_current()
google_app = SocialApp.objects.filter(provider='google').first()

if not google_app:
    google_app = SocialApp.objects.create(
        provider='google',
        name='Google OAuth',
        client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID', 'placeholder'),
        secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', 'placeholder'),
    )
    google_app.sites.add(site)
    print("Created Google OAuth app")
```

## Environment Configuration

Edit `.env` for local settings:

```bash
# Required
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite by default)
DATABASE_URL=sqlite:///db.sqlite3

# Google OAuth (optional for social login)
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-secret
```

## Next Steps

Once your server is running:

1. **Browse cards:** Visit http://localhost:8000/cards/
2. **Create a spending profile:** Add your monthly spending
3. **Generate a roadmap:** Get personalized card recommendations
4. **Explore the API:** Visit http://localhost:8000/api/

## Additional Documentation

- **Project Overview:** [CLAUDE.md](CLAUDE.md)
- **Quick Reference:** [QUICKSTART.md](QUICKSTART.md)
- **Product Requirements:** [PRD.md](PRD.md)
- **Full Documentation:** [README.md](README.md)

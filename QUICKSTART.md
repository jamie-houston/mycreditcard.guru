# Credit Card Guru - Quick Start Guide

## Interactive Management Script

Run the new interactive management script for easy project management:

```bash
source venv/bin/activate
python manage_project.py
```

Or make it executable and run directly:

```bash
./manage_project.py
```

## Menu Options

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

## First Time Setup

If you're setting up the project for the first time:

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Run the management script:**
   ```bash
   python manage_project.py
   ```

3. **Select option 3** - Reset database
   - This will create a fresh database
   - You'll be prompted to create a superuser (recommended)
   - All initial data will be imported automatically

4. **Select option 1** - Run development server
   - Visit http://127.0.0.1:8000/

## Common Tasks

### Import Credit Card Data Only

If your database is already set up but missing card data:

```bash
python manage_project.py
# Select option 5 (Import credit card data)
# Select option 1 (Import ALL data)
```

### Run Tests

```bash
python manage_project.py
# Select option 2 (Run tests)
# Select option 1 (Run all tests)
```

### Create Superuser for Admin Access

```bash
python manage_project.py
# Select option 7 (Manage superuser)
# Select option 1 (Create new superuser)
```

Then access the admin at: http://127.0.0.1:8000/admin/

### Check Database Status

```bash
python manage_project.py
# Select option 6 (Show database info)
```

This shows counts of:
- Credit Cards
- Issuers
- Spending Categories
- Users
- Roadmaps

## Manual Commands (Alternative)

If you prefer running commands directly:

```bash
# Activate environment
source venv/bin/activate

# Run server
python manage.py runserver

# Import all data (recommended for first time)
python setup_data.py

# Import specific issuer cards
python manage.py import_cards data/input/cards/chase.json

# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser

# Database migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

## Debugging in Cursor/VS Code

Press **F5** to start debugging with these configurations:

- **Django: Run Server** - Normal server with hot-reload
- **Django: Run Server (Debug)** - Server without reload (better for breakpoints)
- **Django: Run Tests** - Run test suite in debugger
- **Django: Shell** - Interactive Django shell
- **Django: Migrate** - Run migrations
- **Django: Create Superuser** - Create admin user

## Troubleshooting

### "No credit cards found"

Your database is empty. Run:
```bash
python manage_project.py
# Select option 5 → option 1 (Import ALL data)
```

### "Virtual environment not activated"

```bash
source venv/bin/activate
```

### Port 8000 already in use

Kill the existing server:
```bash
lsof -ti:8000 | xargs kill -9
```

Or use a different port:
```bash
python manage.py runserver 8001
```

### "DoesNotExist: SocialApp matching query does not exist"

This was already fixed during your initial setup. The Google OAuth app has been configured in your database.

## Project Structure

- `/cards/` - Credit card models and APIs
- `/roadmaps/` - Recommendation engine and roadmap generation
- `/users/` - User management and authentication
- `/data/input/` - JSON data files for import
  - `/system/` - Categories, issuers, reward types
  - `/cards/` - Card data by issuer
- `/templates/` - Django HTML templates

## Environment Variables

Edit `.env` file for configuration:

- `SECRET_KEY` - Django secret key
- `DEBUG` - Enable/disable debug mode
- `DATABASE_URL` - Database connection string
- `GOOGLE_OAUTH_CLIENT_ID` - Google OAuth credentials
- `GOOGLE_OAUTH_CLIENT_SECRET` - Google OAuth credentials
- `ALLOWED_HOSTS` - Allowed hostnames

## Additional Resources

- **Project Overview:** See [CLAUDE.md](CLAUDE.md)
- **Product Requirements:** See [PRD.md](PRD.md)
- **Full Documentation:** See [README.md](README.md)

# Deployment Instructions for PythonAnywhere

This guide provides step-by-step instructions for deploying the Credit Card Guru Django application to PythonAnywhere.

## ⚠️ Production database is MySQL, not SQLite (June 2026)

The June 2026 deploy hit broken NFS file-locking on PythonAnywhere's storage: any
SQLite write commit hung forever (even on freshly created databases in fresh
directories), wedging every web worker. Diagnosis trail: stale `db.sqlite3-journal`,
hot-journal rollback hanging, fresh-DB commits hanging, while raw I/O/fsync/fcntl all
worked. Production therefore runs on PythonAnywhere's bundled MySQL:

- `DATABASE_URL=mysql://foresterh:<password>@foresterh.mysql.pythonanywhere-services.com/foresterh$default`
  in the server `.env`. The current MySQL password lives in `~/.my.cnf` on the server —
  the one in old `.env` copies is stale.
- `mysqlclient` is installed in the server virtualenv only (NOT in requirements.txt, so
  local dev installs don't need MySQL headers; local dev stays on SQLite).
- If you ever revert to SQLite: use an **absolute** path
  (`sqlite:////home/foresterh/...`); a relative `sqlite:///db.sqlite3` resolves against
  the WSGI process's cwd and silently creates a second, empty database. And get
  PythonAnywhere support to confirm file locking works first.

A pre-deploy SQLite backup with the old deployment's users/data is at
`~/db.sqlite3.backup-predeploy` on the server.

## Monthly card-data refresh (scheduled task)

A PythonAnywhere scheduled task (daily 09:15 UTC, acts only on the 1st of the month)
resets `data/input/cards/`, pulls main, and runs `import_external_cards` to refresh
signup bonuses/fees; output appends to `~/import_external.log`.

## Quick Reference: Updating After Git Pull

**Looking for update instructions?** Jump to:
- [Updating Your Application (Full Instructions)](#updating-your-application)
- [Quick Update (Code Only)](#quick-update-no-data-changes)
- [Full Update (Code + Data + DB)](#full-update-code--data--database-changes)

**TL;DR - After `git pull`:**
```bash
workon creditcard_guru
pip install -r requirements.txt
python manage.py migrate
python manage.py import_cards data/input/system/spending_categories.json  # the single category seed
python manage.py import_spending_credits   # must precede card import: card credits resolve these by name
python manage.py import_cards data/input/cards/*.json
python manage.py collectstatic --noinput
# Then reload web app in PythonAnywhere
```

---

## Prerequisites

- A PythonAnywhere account (Beginner plan or higher)
- Git access to your repository
- Basic familiarity with the PythonAnywhere interface

## Step 1: Account Setup

1. Sign up for a PythonAnywhere account at https://www.pythonanywhere.com/
2. Choose an appropriate plan (Beginner plan supports custom domains)
3. Note your username - you'll need this for file paths

## Step 2: Clone Your Repository

1. Open a Bash console from your PythonAnywhere dashboard
2. Clone your repository:
   ```bash
   git clone https://github.com/yourusername/mycreditcard.guru.git
   cd mycreditcard.guru
   ```

## Step 3: Set Up Virtual Environment

1. Create a virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.13 creditcard_guru
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Configure Environment Variables

1. Create a `.env` file in your project root:
   ```bash
   nano .env
   ```

2. Add the following environment variables (replace with your actual values):
   ```env
   SECRET_KEY=your-super-secret-production-key-at-least-50-characters-long
   DEBUG=False
   ALLOWED_HOSTS=yourusername.pythonanywhere.com,your-custom-domain.com
   
   # Database (SQLite is fine for small apps, or use MySQL)
   # DATABASE_URL=mysql://username:password@yourusername.mysql.pythonanywhere-services.com/yourusername$creditcard_guru
   
   # Google OAuth (optional - get from Google Cloud Console)
   GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
   
   # CORS origins (include your domain)
   CORS_ALLOWED_ORIGINS=https://yourusername.pythonanywhere.com,https://your-custom-domain.com
   ```

### Important Security Notes:

#### Generating a SECRET_KEY
Generate a new secret key for production:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

#### Google OAuth Setup (Optional)
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized origins
6. Add callback URL: `https://yourdomain.com/accounts/google/login/callback/`

## Step 5: Database Setup

### Option A: SQLite (Default)
1. Run migrations:
   ```bash
   python manage.py migrate
   ```

2. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

### Option B: MySQL (Recommended for production)
1. Create a MySQL database from PythonAnywhere dashboard
2. Update `.env` with DATABASE_URL
3. Run migrations and create superuser as above

## Step 6: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Step 7: Configure WSGI

1. Go to the Web tab in your PythonAnywhere dashboard
2. Create a new web app:
   - Choose "Manual configuration"
   - Select Python 3.10
   - Set the source code directory: `/home/foresterh/mycreditcard.guru`

3. Edit the WSGI configuration file (`/var/www/yourusername_pythonanywhere_com_wsgi.py`):
   ```python
   import os
   import sys
   
   # Add your project directory to the sys.path
   path = '/home/foresterh/mycreditcard.guru'
   if path not in sys.path:
       sys.path.insert(0, path)
   
   # Set the Django settings module
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creditcard_guru.settings')
   
   # Set up Django
   import django
   from django.core.wsgi import get_wsgi_application
   
   django.setup()
   application = get_wsgi_application()
   ```

4. Set the virtual environment path: `/home/foresterh/.virtualenvs/creditcard_guru`

## Step 8: Configure Static Files

In the Web tab, add these static file mappings:

| URL     | Directory                                    |
|---------|----------------------------------------------|
| /static/ | /home/foresterh/mycreditcard.guru/staticfiles |
| /media/  | /home/foresterh/mycreditcard.guru/media      |

## Step 9: Load Initial Data

**Important**: The `import_cards` command works for all file types (system data and card data). Only cards with `"verified": true` will be imported.

1. Import system data:
   ```bash
   python manage.py import_cards data/input/system/issuers.json
   python manage.py import_cards data/input/system/spending_categories.json
   python manage.py import_cards data/input/system/reward_types.json
   ```

2. Import spending credits (for card benefits):
   ```bash
   python manage.py import_spending_credits
   ```

3. Import credit cards:
   ```bash
   python manage.py import_cards data/input/cards/chase.json
   python manage.py import_cards data/input/cards/american_express.json
   python manage.py import_cards data/input/cards/capital_one.json
   python manage.py import_cards data/input/cards/wells_fargo.json
   python manage.py import_cards data/input/cards/citi.json
   # Add other card files as needed
   ```

4. Import credit types (offers/benefits for roadmap preferences):
   ```bash
   python manage.py import_credit_types
   ```

**Note**: Currently 24 out of 162 cards are marked as verified and will be imported. See [docs/CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) for details on which cards are verified.

## Step 10: Configure Domain (Optional)

1. Go to the Web tab
2. Add your custom domain
3. Update ALLOWED_HOSTS in `.env`
4. Set up SSL certificate (available on paid plans)

## Step 11: Final Testing

1. Reload your web app from the Web tab
2. Visit your application URL
3. Test key functionality:
   - View credit cards
   - Create a roadmap
   - Filter categories
   - Admin panel access

## Ongoing Maintenance

### Updating Your Application

When you pull the latest code changes, follow these steps to update your deployment:

#### 1. Pull Latest Changes
```bash
cd ~/mycreditcard.guru
git pull origin main
```

#### 2. Activate Virtual Environment
```bash
workon creditcard_guru
# Or: source ~/.virtualenvs/creditcard_guru/bin/activate
```

#### 3. Install New Dependencies (if any)
```bash
pip install -r requirements.txt
```

#### 4. Run Database Migrations (if any)
```bash
python manage.py migrate
```

#### 5. Update Credit Card Data

**Important**: Only cards marked with `"verified": true` will be imported. See [docs/CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) for details.

**Option A: Update All Card Data (Recommended)**
```bash
# Import system data (categories, issuers, reward types)
python manage.py import_cards data/input/system/issuers.json
python manage.py import_cards data/input/system/spending_categories.json
python manage.py import_cards data/input/system/reward_types.json

# Import spending credits (for card benefits)
python manage.py import_spending_credits

# Import all credit card files
python manage.py import_cards data/input/cards/american_express.json
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/capital_one.json
python manage.py import_cards data/input/cards/wells_fargo.json
python manage.py import_cards data/input/cards/citi.json
python manage.py import_cards data/input/cards/bank_of_america.json
python manage.py import_cards data/input/cards/barclays.json
python manage.py import_cards data/input/cards/us_bank.json
# Add other issuers as needed...

# Import credit types (benefits/offers for preferences)
python manage.py import_credit_types
```

**Option B: Use Setup Script (Fresh Import)**
```bash
python setup_data.py
```
⚠️ **Warning**: This will delete and recreate all data!

**Option C: Update Specific Issuers Only**
```bash
# Just update Chase cards
python manage.py import_cards data/input/cards/chase.json

# Or update a few specific issuers
python manage.py import_cards data/input/cards/american_express.json
python manage.py import_cards data/input/cards/capital_one.json
```

**Notes on Card Imports**:
- The `import_cards` command updates existing cards and creates new ones
- Only cards with `"verified": true` in the JSON are imported
- Currently 24 out of 162 cards are verified for import
- See which cards are verified: [docs/CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md)

#### 6. Collect Static Files (if frontend changed)
```bash
python manage.py collectstatic --noinput
```

#### 7. Reload Web App
Go to the PythonAnywhere Web tab and click **Reload** button

#### 8. Verify Update
- Visit your site and check that changes are live
- Test any new features
- Check error logs if issues occur

### Quick Update (No Data Changes)

If you only changed code (no database or card data changes):
```bash
cd ~/mycreditcard.guru
git pull origin main
python manage.py collectstatic --noinput
# Click Reload in Web tab
```

### Full Update (Code + Data + Database Changes)

For major updates with database and card data changes:
```bash
cd ~/mycreditcard.guru
workon creditcard_guru
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py import_cards data/input/system/*.json
python manage.py import_spending_credits
python manage.py import_cards data/input/cards/*.json
python manage.py import_credit_types
python manage.py collectstatic --noinput
# Click Reload in Web tab
```

### Environment Variables Security

- Never commit your `.env` file to version control
- Use different SECRET_KEY values for development and production
- Regularly rotate sensitive credentials
- Keep DEBUG=False in production

### Monitoring and Logs

- Check error logs from the Web tab
- Monitor resource usage from Dashboard
- Set up database backups for important data

## Troubleshooting

### Common Issues

1. **ImportError or ModuleNotFoundError**
   - Check virtual environment path in Web tab
   - Ensure all dependencies are installed

2. **Static files not loading**
   - Verify static file mappings in Web tab
   - Run `python manage.py collectstatic` again

3. **Database errors**
   - Check DATABASE_URL in `.env`
   - Verify database permissions

4. **Secret key warnings**
   - Generate a new SECRET_KEY for production
   - Ensure it's at least 50 characters long

### Getting Help

- PythonAnywhere Help Pages: https://help.pythonanywhere.com/
- Django Documentation: https://docs.djangoproject.com/
- Check application logs in the Web tab

## Security Checklist

- [ ] DEBUG=False in production
- [ ] Strong, unique SECRET_KEY
- [ ] ALLOWED_HOSTS properly configured
- [ ] SSL certificate enabled (paid plans)
- [ ] Database credentials secured
- [ ] Regular backups configured
- [ ] Environment variables not in version control

## Performance Optimization

For better performance on PythonAnywhere:

1. Use database connection pooling
2. Implement caching where appropriate
3. Optimize database queries
4. Consider upgrading to a higher plan for more resources

---

**Note**: Replace `yourusername` with your actual PythonAnywhere username throughout these instructions.
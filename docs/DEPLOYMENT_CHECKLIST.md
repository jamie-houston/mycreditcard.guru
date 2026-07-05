# PythonAnywhere Deployment Checklist

Use this checklist to ensure a successful deployment to PythonAnywhere.

## Pre-Deployment

- [ ] PythonAnywhere account created
- [ ] Repository is up to date and pushed to GitHub
- [ ] All secrets removed from code and settings.py
- [ ] Requirements.txt includes all production dependencies

## Environment Setup

- [ ] Virtual environment created (`mkvirtualenv`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Repository cloned to PythonAnywhere

## Configuration

- [ ] `.env` file created with production values
- [ ] `SECRET_KEY` generated and configured (50+ characters)
- [ ] `DEBUG=False` set in `.env`
- [ ] `ALLOWED_HOSTS` configured with your domain
- [ ] Database configured (SQLite or MySQL)

## WSGI Configuration

- [ ] Web app created in PythonAnywhere dashboard
- [ ] WSGI file configured with correct paths
- [ ] Virtual environment path set in Web tab
- [ ] Source code directory set correctly

## Static Files

- [ ] Static file mappings configured in Web tab:
  - [ ] `/static/` → `/home/username/mycreditcard.guru/staticfiles`
  - [ ] `/media/` → `/home/username/mycreditcard.guru/media`
- [ ] `python manage.py collectstatic` run successfully

## Database Setup

- [ ] Migrations run (`python manage.py migrate`)
- [ ] Superuser created (`python manage.py createsuperuser`)
- [ ] Initial data loaded:
  - [ ] Spending categories
  - [ ] Issuers
  - [ ] Reward types
  - [ ] Credit cards

## Security Configuration

- [ ] Strong `SECRET_KEY` configured
- [ ] `DEBUG=False` in production
- [ ] HTTPS enabled (paid plans)
- [ ] Security headers configured
- [ ] Google OAuth configured (if using)

## Testing

- [ ] Web app reloaded
- [ ] Homepage loads correctly
- [ ] Admin panel accessible
- [ ] Credit cards display properly
- [ ] Roadmap functionality works
- [ ] Filters work on all pages
- [ ] No console errors in browser

## Optional Features

- [ ] Custom domain configured
- [ ] SSL certificate installed
- [ ] Google OAuth working
- [ ] Email settings configured

## Post-Deployment

- [ ] Error logs checked for issues
- [ ] Performance tested
- [ ] Backup strategy implemented
- [ ] Update procedures documented

## Environment Variables Checklist

Required:
- [ ] `SECRET_KEY`
- [ ] `DEBUG`
- [ ] `ALLOWED_HOSTS`

Optional:
- [ ] `DATABASE_URL`
- [ ] `GOOGLE_OAUTH_CLIENT_ID`
- [ ] `GOOGLE_OAUTH_CLIENT_SECRET`
- [ ] `CORS_ALLOWED_ORIGINS`

## Common Issues Resolved

- [ ] Virtual environment path correct
- [ ] Python path includes project directory
- [ ] Static files collected and mapped
- [ ] Database permissions correct
- [ ] All dependencies installed

---

## Update After Git Pull Checklist

Use this when updating an existing deployment:

### Code Updates
- [ ] SSH into PythonAnywhere console
- [ ] Navigate to project: `cd ~/mycreditcard.guru`
- [ ] Activate virtual environment: `workon creditcard_guru`
- [ ] Pull latest changes: `git pull origin main`
- [ ] Check what changed: review commit messages

### Dependencies & Database
- [ ] Update dependencies: `pip install -r requirements.txt`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Check for migration errors in output

### Card Data Updates
- [ ] Import system data (if changed):
  - [ ] `python manage.py import_cards data/input/system/issuers.json`
  - [ ] `python manage.py import_cards data/input/system/spending_categories.json`
  - [ ] `python manage.py import_cards data/input/system/reward_types.json`
- [ ] Import spending credits: `python manage.py import_spending_credits`
- [ ] Import card data:
  - [ ] `python manage.py import_cards data/input/cards/*.json`
  - [ ] Or specific issuers that changed

### Static Files & Reload
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Go to PythonAnywhere Web tab
- [ ] Click **Reload** button
- [ ] Wait for reload to complete

### Verification
- [ ] Visit your site URL
- [ ] Check homepage loads
- [ ] Test new features/changes
- [ ] Check browser console for errors
- [ ] Check PythonAnywhere error log (Web tab)
- [ ] Verify card data updated correctly

### Quick Update (No Data/DB Changes)
If only code changed:
- [ ] `git pull origin main`
- [ ] `python manage.py collectstatic --noinput`
- [ ] Reload web app
- [ ] Test changes

---

**Remember**: Never commit your `.env` file to version control!
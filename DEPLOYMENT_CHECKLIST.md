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

**Remember**: Never commit your `.env` file to version control!
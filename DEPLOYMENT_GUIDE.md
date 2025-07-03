# Deployment Instructions for PythonAnywhere

This guide provides step-by-step instructions for deploying the Credit Card Guru Django application to PythonAnywhere.

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

1. Load initial data for your application:
   ```bash
   python manage.py loaddata data/input/spending_categories.json
   python manage.py loaddata data/input/issuers.json
   python manage.py loaddata data/input/reward_types.json
   ```

2. Import credit cards:
   ```bash
   python manage.py import_cards data/input/chase.json
   python manage.py import_cards data/input/american_express.json
   python manage.py import_cards data/input/capital_one.json
   python manage.py import_cards data/input/citi.json
   ```

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

1. Pull latest changes:
   ```bash
   cd ~/mycreditcard.guru
   git pull origin main
   ```

2. Install new dependencies (if any):
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations (if any):
   ```bash
   python manage.py migrate
   ```

4. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

5. Reload the web app from PythonAnywhere dashboard

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
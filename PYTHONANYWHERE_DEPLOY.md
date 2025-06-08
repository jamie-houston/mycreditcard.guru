# Deploying to PythonAnywhere

This guide walks through deploying the Credit Card Roadmap application to PythonAnywhere.

## Prerequisites

- A PythonAnywhere account (free tier works fine for basic usage)
- Google OAuth credentials (Client ID and Client Secret)
- Custom domain (optional)

## Setup Steps

### 1. Sign Up and Create a Web App

1. Sign up for a PythonAnywhere account at https://www.pythonanywhere.com/
2. From your dashboard, click on the **Web** tab
3. Click **Add a new web app**
4. Choose **Manual configuration** (not the "Flask" option)
5. Select **Python 3.11**

### 2. Set Up Your Code

1. In the PythonAnywhere dashboard, go to the **Consoles** tab
2. Start a new Bash console
3. Clone your repository:
   ```bash
   git clone https://github.com/jamie-houston/creditcard-roadmap.git
   ```
   
   If using a private repository, set up an SSH key or use HTTPS with a personal access token.

### 3. Configure Virtual Environment

1. In the Bash console, create and activate a virtual environment:
   ```bash
   cd creditcard-roadmap
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   cd flask_app
   pip install -r requirements.txt
   ```

### 4. Configure Google OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Create a new OAuth 2.0 Client ID or edit your existing one
4. Add the following to "Authorized JavaScript origins":
   ```
   https://yourdomain.com
   ```
5. Add the following to "Authorized redirect URIs":
   ```
   https://yourdomain.com/login/google/authorized
   ```
   Replace `yourdomain.com` with your actual domain (either custom domain or `yourusername.pythonanywhere.com`)
6. Save your changes and note your Client ID and Client Secret

### 5. Configure Environment Variables

1. Click the **Web** tab in PythonAnywhere
2. Scroll down to the **Environment variables** section and add:
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: `your-secure-secret-key`
   - `GOOGLE_OAUTH_CLIENT_ID`: `your-google-client-id`
   - `GOOGLE_OAUTH_CLIENT_SECRET`: `your-google-client-secret`
   - `OAUTHLIB_RELAX_TOKEN_SCOPE`: `1`
   - `PYTHONANYWHERE_DOMAIN`: `yourdomain.com` (if using a custom domain)

### 6. Custom Domain Setup (Optional)

If you're using a custom domain:

1. Go to the **Web** tab in PythonAnywhere
2. Scroll down to the **Add a new domain** section
3. Enter your domain name and click "Add"
4. Follow the instructions to configure your DNS settings
5. Make sure to add the `PYTHONANYWHERE_DOMAIN` environment variable with your custom domain

### 7. Configure Web App

1. Go back to the **Web** tab
2. In the **Code** section:
   - Set **Source code** to: `/home/yourusername/creditcard-roadmap/flask_app` 
   - Set **Working directory** to: `/home/yourusername/creditcard-roadmap/flask_app`

3. In the **Virtualenv** section:
   - Enter: `/home/yourusername/creditcard-roadmap/venv`

4. In the **WSGI configuration file** section, click the link to edit the WSGI file

5. Make sure the WSGI file has the correct contents from your `flask_app/wsgi.py` file:
   ```python
   """
   WSGI configuration for PythonAnywhere deployment.
   This file helps PythonAnywhere understand how to run your Flask application.
   """
   
   import sys
   import os
   import logging
   
   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   logger = logging.getLogger('creditcard_roadmap')
   
   # Add the project root directory to the path
   path = os.path.dirname(__file__)
   if path not in sys.path:
       sys.path.append(path)
       logger.info(f"Added {path} to sys.path")
   
   # Set OAuth environment variables for PythonAnywhere
   os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
   logger.info("Set OAUTHLIB_RELAX_TOKEN_SCOPE=1")
   
   # Only enforce HTTPS in production
   if '/home/' in path:
       # We're on PythonAnywhere
       os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
       logger.info("Set OAUTHLIB_INSECURE_TRANSPORT=0 for production")
       
       # Check for custom domain environment variable
       custom_domain = os.environ.get('PYTHONANYWHERE_DOMAIN')
       if not custom_domain:
           # If no custom domain is set, default to standard PythonAnywhere domain
           username = path.split('/home/')[1].split('/')[0]
           os.environ['PYTHONANYWHERE_DOMAIN'] = f'{username}.pythonanywhere.com'
           custom_domain = f'{username}.pythonanywhere.com'
       
       logger.info(f"Using domain for OAuth: {custom_domain}")
   else:
       # Local development
       os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
       logger.info("Set OAUTHLIB_INSECURE_TRANSPORT=1 for development")
   
   # Create application instance
   try:
       from app import create_app
       application = create_app('production')
       logger.info("Application created successfully")
   except Exception as e:
       logger.error(f"Error creating application: {str(e)}", exc_info=True)
       raise
   ```

### 8. Set Up Static Files

1. Go back to the **Web** tab
2. In the **Static files** section, add:
   - URL: `/static/`
   - Path: `/home/yourusername/creditcard-roadmap/flask_app/app/static`

### 9. Initialize the Database

1. In the Bash console, initialize the database:
   ```bash
   cd ~/creditcard-roadmap/flask_app
   source ../venv/bin/activate
   export FLASK_APP=wsgi.py
   flask db upgrade
   ```

   If the above command fails, you may need to create the database from scratch:
   ```bash
   python -c "from app import create_app; from app import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

### 10. Reload and Test

1. Click the **Reload** button to restart your web app
2. Visit your site at your domain
3. Test the Google login functionality

## Troubleshooting

### OAuth Issues

If you encounter OAuth-related errors:

1. **Check error logs**: 
   - Go to the Web tab and check the error log
   - Look for OAuth related errors in the logs

2. **Verify Google Credentials**:
   - Double-check that your Google OAuth Client ID and Secret are correct
   - Ensure the authorized redirect URIs exactly match your application paths:
     - The domain should be your actual domain (custom or PythonAnywhere)
     - The path should be `/login/google/authorized`

3. **Environment Variables**:
   - Make sure all the required environment variables are set correctly
   - For custom domains, ensure `PYTHONANYWHERE_DOMAIN` is set to your domain

4. **WSGI File**:
   - Check that the WSGI file is correctly detecting your domain
   - You can add print statements to the WSGI file to debug domain detection

### Custom Domain Issues

If you're having issues with a custom domain:

1. Verify your DNS settings are correctly pointing to PythonAnywhere
2. Make sure HTTPS is properly configured for your custom domain
3. Check that the `PYTHONANYWHERE_DOMAIN` environment variable is set correctly
4. Ensure your Google OAuth redirect URI matches the exact domain

### Database Issues

If you encounter database errors:

```bash
cd ~/creditcard-roadmap/flask_app
source ../venv/bin/activate
export FLASK_APP=wsgi.py

# Reset the database if needed
flask db stamp head
flask db migrate
flask db upgrade
```

## Maintenance

- **Database migrations**: Run database migrations after code updates:
  ```bash
  cd ~/creditcard-roadmap/flask_app
  source ../venv/bin/activate
  export FLASK_APP=wsgi.py
  flask db upgrade
  ```
  
- **Code updates**: Pull the latest code and reload the web app:
  ```bash
  cd ~/creditcard-roadmap
  git pull
  source venv/bin/activate
  pip install -r requirements.txt
  ```
  Then click the **Reload** button in the Web tab. 
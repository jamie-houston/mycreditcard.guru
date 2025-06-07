"""
WSGI configuration for PythonAnywhere deployment.
This file helps PythonAnywhere understand how to run your Flask application.
"""

import sys
import os

# Add the project root directory to the path
path = os.path.dirname(__file__)
if path not in sys.path:
    sys.path.append(path)

# Set OAuth environment variables for PythonAnywhere
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Only enforce HTTPS in production
if '/home/' in path:
    # We're on PythonAnywhere
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
    
    # Extract username from path for domain configuration
    username = path.split('/home/')[1].split('/')[0]
    os.environ['PYTHONANYWHERE_DOMAIN'] = f'{username}.pythonanywhere.com'
    print(f"Setting PythonAnywhere domain to: {username}.pythonanywhere.com")
else:
    # Local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Create application instance
from app import create_app
application = create_app('production') 
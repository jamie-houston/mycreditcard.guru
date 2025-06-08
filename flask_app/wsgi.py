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
    
    # Extract username from path for domain configuration
    logger.info(f"PythonAnywhere domain is: {os.environ.get('PYTHONANYWHERE_DOMAIN')}")
else:
    # Local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    logger.info("Set OAUTHLIB_INSECURE_TRANSPORT=1 for development")

# Set additional OAuth debugging
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    logging.getLogger('flask_dance').setLevel(logging.DEBUG)
    logging.getLogger('oauthlib').setLevel(logging.DEBUG)
    logging.getLogger('requests_oauthlib').setLevel(logging.DEBUG)
    logger.info("Enabled OAuth debug logging for development")

logger.info("Starting application...")

# Create application instance
try:
    from app import create_app
    application = create_app('production')
    logger.info("Application created successfully")
except Exception as e:
    logger.error(f"Error creating application: {str(e)}", exc_info=True)
    raise 
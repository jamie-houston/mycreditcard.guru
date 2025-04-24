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

# Create application instance
from app import create_app
application = create_app('production') 
"""
WSGI configuration for PythonAnywhere deployment.
This file helps PythonAnywhere understand how to run your Flask application.
"""

import sys
import os

# Add the parent directory (project root) to the path
path = os.path.dirname(os.path.dirname(__file__))
if path not in sys.path:
    sys.path.append(path)

# Create application instance
from creditcard_roadmap.app import create_app
application = create_app('production') 
# wsgi.py Usage Documentation

## Executive Summary
The `wsgi.py` module is Django's Web Server Gateway Interface (WSGI) configuration file that serves as the entry point for production deployment servers. It configures the Django application for WSGI-compatible web servers like Gunicorn, uWSGI, and mod_wsgi, enabling the Credit Card Guru application to run in production environments.

## Module Overview
`wsgi.py` is Django's auto-generated WSGI application configuration script that provides the standard interface between Python web applications and web servers. It establishes the application callable that WSGI servers use to serve the Django application in production deployments.

### Key Responsibilities:
- **WSGI Application Interface**: Provides the standard `application` callable required by WSGI specification for web server integration
- **Django Environment Configuration**: Sets up the Django settings module and initializes the application environment for production use
- **Production Deployment Bridge**: Serves as the connection point between Django application code and production web servers

## Initialization
This module is automatically used by WSGI servers and should not be run directly. It's configured through web server configuration files that reference the application callable.

```python
# WSGI server configuration (e.g., Gunicorn)
gunicorn creditcard_guru.wsgi:application

# In production server configurations (Apache, Nginx + uWSGI)
# The WSGI server loads this module and calls the application
from creditcard_guru.wsgi import application
```

## Public API documentation

### `application`
The WSGI application callable that serves as the main entry point for production deployment.
- **Type**: Django WSGI application instance
- **Purpose**: Handles HTTP requests and responses according to WSGI specification
- **Configuration**: Automatically configured with 'creditcard_guru.settings' module
- **Usage**: Referenced by WSGI servers to serve the Django application

## Dependencies

### External Dependencies
- **os**: Environment variable management for Django settings configuration
- **django.core.wsgi**: Django's WSGI application handler and request processing framework

### Internal Dependencies
- **creditcard_guru.settings**: Django project settings module providing application configuration
- **Django Framework**: Complete Django application stack with all installed apps and middleware

## Practical Code Examples

### Example 1: Gunicorn Production Deployment (Primary Use Case)
Standard production deployment using Gunicorn WSGI server to serve the Credit Card Guru application.

```python
# Command line deployment
gunicorn creditcard_guru.wsgi:application --bind 0.0.0.0:8000 --workers 3

# Gunicorn configuration file (gunicorn.conf.py)
bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
preload_app = True
wsgi_module = "creditcard_guru.wsgi:application"

# Systemd service file
# [Service]
# ExecStart=/path/to/venv/bin/gunicorn creditcard_guru.wsgi:application
# WorkingDirectory=/path/to/creditcard_guru/
# Environment=DJANGO_SETTINGS_MODULE=creditcard_guru.settings
```

### Example 2: Apache mod_wsgi Configuration (Secondary Use Case)
Alternative production deployment using Apache web server with mod_wsgi module.

```python
# Apache virtual host configuration
# <VirtualHost *:80>
#     ServerName mycreditcard.guru
#     DocumentRoot /path/to/creditcard_guru/
#     
#     WSGIDaemonProcess creditcard_guru python-path=/path/to/creditcard_guru python-home=/path/to/venv
#     WSGIProcessGroup creditcard_guru
#     WSGIScriptAlias / /path/to/creditcard_guru/wsgi.py
#     
#     <Directory /path/to/creditcard_guru>
#         WSGIApplicationGroup %{GLOBAL}
#         Require all granted
#     </Directory>
# </VirtualHost>

# Custom WSGI wrapper (if needed)
import os
import sys
from django.core.wsgi import get_wsgi_application

# Add project directory to Python path
sys.path.append('/path/to/creditcard_guru')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creditcard_guru.settings')

application = get_wsgi_application()
```

# wsgi.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `creditcard_guru/wsgi.py` module, which contains the WSGI (Web Server Gateway Interface) configuration for the Django project. This module provides the WSGI application interface that web servers use to serve the credit card recommendation platform in production environments.

## Module Overview
`creditcard_guru/wsgi.py` is the WSGI application module that serves as the interface between web servers and the Django application. It configures the Django settings module and creates the WSGI application object that production web servers use to serve the application.

### Key Responsibilities:
- **WSGI Application Interface**: Provides the standard WSGI application callable that web servers (Apache, Nginx + Gunicorn, etc.) use to serve the Django application
- **Django Settings Configuration**: Sets the DJANGO_SETTINGS_MODULE environment variable to point to the project's settings configuration
- **Production Deployment Interface**: Serves as the entry point for production web server deployments and WSGI container integration


## Initialization
The `creditcard_guru/wsgi.py` file is loaded by WSGI-compatible web servers. It sets up the Django application for production deployment.

```python
# WSGI server initialization (e.g., Gunicorn)
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creditcard_guru.settings')
application = get_wsgi_application()
```

## Public API documentation

### WSGI Application Interface
Provides the standard WSGI application callable for web server integration.

#### Core Interface:
- **application**: WSGI application callable that web servers use to serve requests
- **Environment Setup**: Configures Django settings module for production
- **Production Ready**: Optimized for production web server deployment

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: Gunicorn Production Deployment
How to use wsgi.py with Gunicorn for production deployment.

```bash
# Production deployment with Gunicorn
gunicorn --bind 0.0.0.0:8000 creditcard_guru.wsgi:application

# With additional workers for better performance
gunicorn --workers 4 --bind 0.0.0.0:8000 creditcard_guru.wsgi:application
```

### Example 2: Apache mod_wsgi Configuration
How to configure Apache to use the WSGI application.

```apache
# In Apache virtual host configuration
<VirtualHost *:80>
    ServerName mycreditcard.guru
    
    WSGIDaemonProcess creditcard_guru python-path=/path/to/project
    WSGIProcessGroup creditcard_guru
    WSGIScriptAlias / /path/to/project/creditcard_guru/wsgi.py
    
    <Directory /path/to/project/creditcard_guru>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
</VirtualHost>
```


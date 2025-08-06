# settings.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `creditcard_guru/settings.py` module, which contains the main Django project settings and configuration. This module defines all Django project settings including database configuration, installed apps, middleware, authentication, API settings, and environment-specific configurations for the credit card recommendation platform.

## Module Overview
`creditcard_guru/settings.py` is the central Django settings module that configures the entire project. It contains database settings, installed Django apps, middleware configuration, REST framework settings, authentication backends, and other project-wide configurations.

### Key Responsibilities:
- **Django Project Configuration**: Defines core Django settings including SECRET_KEY, DEBUG mode, ALLOWED_HOSTS, and database configuration for the credit card platform
- **Application Registration**: Lists all installed Django apps including cards, roadmaps, users, and third-party packages like Django REST Framework
- **Middleware & Authentication Setup**: Configures middleware stack, authentication backends, session handling, and security settings for API access


## Initialization
The `creditcard_guru/settings.py` file is automatically loaded by Django when the project starts. It's imported via the DJANGO_SETTINGS_MODULE environment variable.

```python
# Environment variable in production/development
export DJANGO_SETTINGS_MODULE=creditcard_guru.settings

# Django automatically loads settings during startup
# No manual initialization required
```

## Public API documentation

### Configuration Variables
Provides Django configuration through module-level variables.

#### Core Settings:
- **DEBUG**: Development/production mode toggle
- **SECRET_KEY**: Cryptographic signing key for sessions
- **DATABASES**: Database connection configuration
- **INSTALLED_APPS**: List of Django applications
- **MIDDLEWARE**: Request/response processing middleware stack
- **REST_FRAMEWORK**: Django REST Framework configuration

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: Environment-Specific Configuration
How settings.py handles different environments (development vs production).

```python
# In settings.py - environment-specific configuration
import os
from pathlib import Path

# Development vs Production
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-here')

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Example 2: Application Registration
How Django apps are registered and configured in settings.

```python
# In settings.py - app registration
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'rest_framework',
    'cards',         # Credit card models and logic
    'roadmaps',      # Recommendation engine
    'users',         # User profiles and preferences
]

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```


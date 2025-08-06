# apps.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `roadmaps/apps.py` module, which contains the standard Django application configuration for the roadmaps module. This module defines the RoadmapsConfig class that configures the roadmaps application within the Django project, setting up the default auto field and application name for the recommendation roadmap functionality.

## Module Overview
`roadmaps/apps.py` is a 7-line standard Django application configuration module that provides the essential app configuration for the roadmaps module. It follows Django's standard app configuration pattern and is automatically loaded by Django during application startup.

### Key Responsibilities:
- **Django App Configuration**: Defines the RoadmapsConfig class that inherits from Django's AppConfig to configure the roadmaps application
- **Auto Field Setup**: Configures the default_auto_field to use BigAutoField for automatic primary key generation in roadmaps models
- **App Registration**: Provides the proper app name registration so Django can discover and load the roadmaps module and its components


## Initialization
This module is automatically initialized by Django during application startup. No manual initialization required.

```python
# Automatically configured in settings.py INSTALLED_APPS
INSTALLED_APPS = [
    # ... other apps
    'roadmaps',  # Django automatically loads roadmaps.apps.RoadmapsConfig
    # ... other apps
]

# The RoadmapsConfig class is automatically instantiated by Django
from django.apps import AppConfig

class RoadmapsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'roadmaps'
```

## Public API documentation

### `RoadmapsConfig` Class
Standard Django application configuration class.

#### Properties:
- **`default_auto_field`**: Set to 'django.db.models.BigAutoField' for 64-bit integer primary keys
- **`name`**: Set to 'roadmaps' - the Python path to the application module

#### Methods:
Inherits all methods from Django's `AppConfig` base class including:
- **`ready()`**: Called when Django starts (can be overridden for startup tasks)
- **`get_models()`**: Returns all models registered in this app
- **`get_model(model_name)`**: Retrieves a specific model by name

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: Standard Django App Configuration
This is the standard pattern for Django app configuration - no custom usage required.

```python
# In settings.py - automatically handled
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'roadmaps',  # Loads roadmaps.apps.RoadmapsConfig automatically
    'cards',
    'users',
]
```

### Example 2: Accessing App Configuration at Runtime
Rarely needed, but you can access the app config if required.

```python
from django.apps import apps

# Get the roadmaps app configuration
roadmaps_config = apps.get_app_config('roadmaps')
print(f"App name: {roadmaps_config.name}")
print(f"Default auto field: {roadmaps_config.default_auto_field}")

# Get all models in the roadmaps app
roadmaps_models = roadmaps_config.get_models()
for model in roadmaps_models:
    print(f"Model: {model.__name__}")
```


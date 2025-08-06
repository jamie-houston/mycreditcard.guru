# urls.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `creditcard_guru/urls.py` module, which contains the main Django project URL configuration. This module defines the root URL routing for the entire credit card recommendation platform, mapping URLs to Django apps and admin interface with proper URL namespacing and organization.

## Module Overview
`creditcard_guru/urls.py` is the root Django URL configuration module that handles URL routing for the entire project. It includes URLs for the Django admin interface, API endpoints for cards, roadmaps, and users apps, and handles static file serving in development.

### Key Responsibilities:
- **Root URL Routing**: Defines the main URL patterns for the entire Django project, routing requests to appropriate apps (cards, roadmaps, users)
- **Admin Interface Routing**: Configures access to Django's admin interface at /admin/ for data management and administrative tasks
- **API Endpoint Organization**: Maps API URLs with proper prefixes (/api/cards/, /api/roadmaps/, /api/users/) to their respective app URL configurations


## Initialization
The `creditcard_guru/urls.py` file is automatically loaded by Django's URL resolution system. It's referenced in settings.py as ROOT_URLCONF.

```python
# In settings.py
ROOT_URLCONF = 'creditcard_guru.urls'

# Django automatically processes URL patterns during request routing
# No manual initialization required
```

## Public API documentation

### URL Patterns
Defines URL routing patterns for the entire Django project.

#### Core URL Mappings:
- **Admin Interface**: `/admin/` - Django admin interface
- **API Endpoints**: `/api/cards/`, `/api/roadmaps/`, `/api/users/` - REST API endpoints
- **Static Files**: Development static file serving
- **App Inclusion**: Routes to individual app URL configurations

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: API Endpoint Routing
How the main URLs file routes API requests to individual app URL configurations.

```python
# In creditcard_guru/urls.py - API routing
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/cards/', include('cards.urls')),
    path('api/roadmaps/', include('roadmaps.urls')),
    path('api/users/', include('users.urls')),
]

# Routes requests like /api/cards/recommendations/ to cards.urls
```

### Example 2: Static File Handling
How URLs configuration handles static files in development.

```python
# In creditcard_guru/urls.py - development static files
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... other patterns
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```


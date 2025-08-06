# urls.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `roadmaps/urls.py` module, which defines URL routing patterns for the roadmaps Django app. These URL patterns map API endpoints for roadmap management, filter operations, recommendation generation, and debugging utilities with clean RESTful API design for the roadmap functionality.

## Module Overview
`roadmaps/urls.py` is a 24-line Django URL configuration module that defines the routing patterns for the roadmaps application. It provides endpoints for roadmap CRUD operations, filter management, recommendation generation, and development utilities.

### Key Responsibilities:
- **Roadmap CRUD URLs**: Maps endpoints for roadmap listing, creation, detail views, and management operations with proper RESTful URL patterns
- **Filter & Generation Endpoints**: Defines URLs for roadmap filters, recommendation generation, and quick recommendation features with parameter handling
- **Development & Debug Routes**: Provides URL patterns for statistics, scenario export, and development utilities to support roadmap feature development

## Initialization
Django URL patterns are automatically loaded when Django starts. No manual initialization required.

```python
# Automatically loaded by Django via main urls.py
# Included as: path('api/roadmaps/', include('roadmaps.urls'))
# All patterns become available at /api/roadmaps/ prefix
```

## Public API documentation

### URL Patterns (API Endpoints)
- **`/api/roadmaps/filters/`**: List available roadmap filter options
- **`/api/roadmaps/`**: List user's roadmaps with filtering and pagination
- **`/api/roadmaps/create/`**: Create new roadmap with filters and user context
- **`/api/roadmaps/<int:pk>/`**: Get detailed roadmap with recommendations and calculations
- **`/api/roadmaps/<int:roadmap_id>/generate/`**: Generate recommendations for existing roadmap
- **`/api/roadmaps/quick-recommendation/`**: Get quick card recommendations without saving
- **`/api/roadmaps/stats/`**: Get roadmap statistics and analytics
- **`/api/roadmaps/export-scenario/`**: Export roadmap data for testing/debugging

### URL Namespacing
All URLs use `app_name = 'roadmaps'` for proper namespacing and reverse URL lookup.

## Dependencies
### External Dependencies:
- `django.urls`: URL routing functionality
- `rest_framework`: DRF URL patterns

### Internal Dependencies:
- `roadmaps.views`: All view functions and classes mapped to URLs
- Used by: Django URL resolver, API clients, roadmap management interfaces

## Practical Code Examples

### Example 1: Roadmap API Endpoint Usage
How to access various roadmap API endpoints.

```python
# GET /api/roadmaps/
# List user's roadmaps
curl -X GET "http://localhost:8000/api/roadmaps/" \
     -H "Authorization: Bearer <token>"

# POST /api/roadmaps/create/
# Create new roadmap with filters
curl -X POST "http://localhost:8000/api/roadmaps/create/" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{
       "name": "Travel Strategy",
       "filters": {"max_annual_fee": "150.00", "preferred_issuer": "Chase"},
       "user_spending": [{"category": "Travel", "amount": "800.00"}]
     }'

# POST /api/roadmaps/5/generate/
# Generate recommendations for roadmap ID 5
curl -X POST "http://localhost:8000/api/roadmaps/5/generate/" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"updated_spending": [{"category": "Travel", "amount": "1000.00"}]}'

# POST /api/roadmaps/quick-recommendation/
# Get quick recommendations without saving
curl -X POST "http://localhost:8000/api/roadmaps/quick-recommendation/" \
     -H "Content-Type: application/json" \
     -d '{
       "spending_profile": [{"category": "Groceries", "amount": "500.00"}],
       "preferences": {"max_annual_fee": "100.00"}
     }'
```

### Example 2: Django URL Reverse Lookup
Using Django's reverse URL lookup with roadmap URLs.

```python
from django.urls import reverse

# Reverse lookup for roadmap list
roadmap_list_url = reverse('roadmaps:roadmap-list')
# Returns: /api/roadmaps/

# Reverse lookup for roadmap creation
create_url = reverse('roadmaps:roadmap-create')
# Returns: /api/roadmaps/create/

# Reverse lookup for roadmap detail
detail_url = reverse('roadmaps:roadmap-detail', kwargs={'pk': 1})
# Returns: /api/roadmaps/1/

# Reverse lookup for recommendation generation
generate_url = reverse('roadmaps:roadmap-generate', kwargs={'roadmap_id': 5})
# Returns: /api/roadmaps/5/generate/

# Use in templates:
# {% url 'roadmaps:roadmap-list' %}
# {% url 'roadmaps:roadmap-detail' roadmap.pk %}
```

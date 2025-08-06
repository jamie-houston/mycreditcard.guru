# urls.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `users/urls.py` module, which defines URL routing patterns for the users Django app. These URL patterns map API endpoints for user authentication, profile management, card operations, and spending data management with comprehensive user account functionality and clean RESTful API design.

## Module Overview
`users/urls.py` is a 26-line Django URL configuration module that defines the routing patterns for the users application. It provides endpoints for user authentication status, profile management, card collection operations, and bulk data management.

### Key Responsibilities:
- **Authentication & Profile URLs**: Maps endpoints for user status checking, profile management, and user preferences with proper authentication handling
- **Card Collection Management**: Defines URL patterns for user card operations including adding, updating, removing, and retrieving card details with detailed card ownership tracking
- **Data Management Endpoints**: Provides URLs for spending data management and bulk user data operations for efficient API interactions

## Initialization
Django URL patterns are automatically loaded when Django starts. No manual initialization required.

```python
# Automatically loaded by Django via main urls.py
# Included as: path('api/users/', include('users.urls'))
# All patterns become available at /api/users/ prefix
```

## Public API documentation

### URL Patterns (API Endpoints)
- **`/api/users/status/`**: Check user authentication status and basic info
- **`/api/users/profile/`**: Get/update user profile with credit card preferences
- **`/api/users/preferences/`**: Manage user UI preferences and notification settings
- **`/api/users/cards/`**: List and manage user's credit card collection
- **`/api/users/cards/<int:pk>/`**: Detailed view/management of specific user cards
- **`/api/users/cards/toggle/`**: Add/remove cards from user's collection
- **`/api/users/cards/update-details/`**: Update user-specific card information
- **`/api/users/cards/details/`**: Retrieve detailed user card collection data
- **`/api/users/spending/`**: Manage user spending profiles and amounts
- **`/api/users/data/`**: Bulk user data operations (get/save all user data)

### URL Namespacing
All URLs use `app_name = 'users'` for proper namespacing and reverse URL lookup.

## Dependencies
### External Dependencies:
- `django.urls`: URL routing functionality
- `rest_framework`: DRF URL patterns

### Internal Dependencies:
- `users.views`: All view functions and classes mapped to URLs
- Used by: Django URL resolver, API clients, user management interfaces

## Practical Code Examples

### Example 1: User API Endpoint Usage
How to access various user API endpoints.

```python
# GET /api/users/status/
# Check user authentication status
curl -X GET "http://localhost:8000/api/users/status/" \
     -H "Authorization: Bearer <token>"

# GET /api/users/profile/
# Get user profile data
curl -X GET "http://localhost:8000/api/users/profile/" \
     -H "Authorization: Bearer <token>"

# PUT /api/users/profile/
# Update user profile
curl -X PUT "http://localhost:8000/api/users/profile/" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"preferred_issuer": "Chase", "max_annual_fee": "150.00"}'

# POST /api/users/cards/toggle/
# Add/remove card from collection
curl -X POST "http://localhost:8000/api/users/cards/toggle/" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"card_id": 5, "action": "add"}'
```

### Example 2: Django URL Reverse Lookup
Using Django's reverse URL lookup with user URLs.

```python
from django.urls import reverse

# Reverse lookup for user profile
profile_url = reverse('users:user-profile')
# Returns: /api/users/profile/

# Reverse lookup for user cards
user_cards_url = reverse('users:user-cards')
# Returns: /api/users/cards/

# Reverse lookup for card detail
card_detail_url = reverse('users:user-card-detail', kwargs={'pk': 1})
# Returns: /api/users/cards/1/

# Use in templates:
# {% url 'users:user-profile' %}
# {% url 'users:user-cards' %}
```

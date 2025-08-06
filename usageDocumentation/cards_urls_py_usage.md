# urls.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/urls.py` module, which defines URL routing patterns for the cards Django app. These URL patterns map API endpoints to their respective views for credit card data, user profiles, recommendations, and card ownership management with comprehensive API endpoint structure.

## Module Overview
`cards/urls.py` is a 35-line Django URL configuration module that defines the routing patterns for the cards application. It maps various API endpoints to class-based and function-based views for handling credit card operations, user interactions, and recommendation features.

### Key Responsibilities:
- **Reference Data Routing**: Maps endpoints for issuers, reward types, spending categories, and spending credits to their respective list views with proper URL patterns
- **Credit Card API Endpoints**: Defines routing for card listings, details, search functionality, and category-specific card recommendations with parameter handling
- **User Interaction URLs**: Provides URL patterns for user profile management, card ownership tracking, and quick recommendation features with authentication handling

## Initialization
Django URL patterns are automatically loaded when Django starts. No manual initialization required.

```python
# Automatically loaded by Django via main urls.py
# Included as: path('api/cards/', include('cards.urls'))
# All patterns become available at /api/cards/ prefix
```

## Public API documentation

### URL Patterns (API Endpoints)
- **`/api/cards/issuers/`**: List all credit card issuers
- **`/api/cards/reward-types/`**: List all reward types
- **`/api/cards/spending-categories/`**: List spending categories
- **`/api/cards/spending-credits/`**: List spending credit types
- **`/api/cards/`**: List credit cards with filtering/pagination
- **`/api/cards/<int:pk>/`**: Get detailed credit card information
- **`/api/cards/search/`**: Advanced credit card search with filters
- **`/api/cards/category/<int:category_id>/`**: Cards optimized for spending category
- **`/api/cards/user-profile/`**: Create/update user spending profile
- **`/api/cards/user-cards/`**: Get user's current card collection
- **`/api/cards/user-cards/add/`**: Add card to user collection
- **`/api/cards/user-cards/remove/`**: Remove card from user collection
- **`/api/cards/quick-recommendation/`**: Get quick card recommendations

### URL Namespacing
All URLs use `app_name = 'cards'` for proper namespacing and reverse URL lookup.

## Dependencies
### External Dependencies:
- `django.urls`: URL routing functionality
- `rest_framework`: DRF URL patterns

### Internal Dependencies:
- `cards.views`: All view functions and classes mapped to URLs
- Used by: Django URL resolver, API clients, frontend applications

## Practical Code Examples

### Example 1: API Endpoint Usage
How to access various card API endpoints.

```python
# GET /api/cards/
# Returns paginated list of credit cards
curl -X GET "http://localhost:8000/api/cards/"

# GET /api/cards/search/?issuer=Chase&annual_fee_max=100
# Search for Chase cards with annual fee under $100
curl -X GET "http://localhost:8000/api/cards/search/?issuer=Chase&annual_fee_max=100"

# GET /api/cards/category/1/
# Get cards optimized for spending category ID 1 (e.g., Groceries)
curl -X GET "http://localhost:8000/api/cards/category/1/"

# POST /api/cards/user-profile/
# Create or update user spending profile
curl -X POST "http://localhost:8000/api/cards/user-profile/" \
     -H "Content-Type: application/json" \
     -d '{"spending_amounts": [{"category": "Groceries", "amount": "500.00"}]}'
```

### Example 2: Django URL Reverse Lookup
Using Django's reverse URL lookup with card URLs.

```python
from django.urls import reverse

# Reverse lookup for card list
card_list_url = reverse('cards:card-list')
# Returns: /api/cards/

# Reverse lookup for card detail
card_detail_url = reverse('cards:card-detail', kwargs={'pk': 1})
# Returns: /api/cards/1/

# Reverse lookup for category cards
category_cards_url = reverse('cards:cards-by-category', kwargs={'category_id': 2})
# Returns: /api/cards/category/2/

# Use in templates:
# {% url 'cards:card-list' %}
# {% url 'cards:card-detail' card.pk %}
```

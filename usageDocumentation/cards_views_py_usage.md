# views.py Usage Documentation

## Executive Summary
This document provides usage documentation for the Django REST Framework views in the cards application, which implement a comprehensive credit card API. These views handle credit card data retrieval, user spending profile management, advanced search functionality, and detailed category analysis, providing the backend API endpoints for a credit card recommendation platform.

## Module Overview
`cards/views.py` contains Django REST Framework view classes and function-based views that implement the API endpoints for the credit card recommendation system. This module provides both list/detail views for reference data and complex business logic views for user interaction, search, and recommendation functionality.

### Key Responsibilities:
- **Reference Data API**: Provides list views for Issuers, RewardTypes, SpendingCategories, and SpendingCredits with efficient query optimization
- **Credit Card API**: Implements comprehensive card listing, filtering, searching, and detail views with complex relationship prefetching
- **User Profile Management**: Handles user spending profile creation, retrieval, and updates for both authenticated and anonymous users
- **Advanced Search & Filtering**: Provides sophisticated card search with multiple filter criteria, pagination, and sorting options
- **Category Analysis**: Offers detailed category views showing top reward rates and card recommendations per spending category

## Initialization
These Django views are automatically registered via URL routing. No manual initialization required.

```python
# Automatically initialized by Django via cards/urls.py
# Access via HTTP requests to mapped URLs:
# GET /api/cards/ -> CreditCardListView
# GET /api/issuers/ -> IssuerListView
# POST /api/user-profile/ -> create_or_update_user_profile
```

## Public API documentation

### Class-Based Views (DRF)
- **`IssuerListView`**: List all credit card issuers
- **`RewardTypeListView`**: List all reward types
- **`SpendingCategoryListView`**: List all spending categories  
- **`SpendingCreditListView`**: List all spending credit types
- **`CreditCardListView`**: List credit cards with filtering/search
- **`CreditCardDetailView`**: Get detailed credit card information
- **`UserSpendingProfileListView`**: Manage user spending profiles

### Function-Based Views
- **`search_cards`**: Advanced credit card search with filters
- **`cards_by_category`**: Get cards optimized for spending category
- **`create_or_update_user_profile`**: User profile management
- **`get_user_cards`**: Get user's current card collection
- **`add_user_card`/`remove_user_card`**: Manage user card ownership
- **`quick_recommendation`**: Get quick card recommendations

### URL Endpoints
All views map to RESTful API endpoints for credit card data access and user management.

## Dependencies
### External Dependencies:
- `django.shortcuts`: Django view utilities
- `rest_framework`: Django REST Framework
- `django.contrib.auth.models.User`: User authentication
- `django.db.models`: Database querying

### Internal Dependencies:
- `cards.models`: All card-related models
- `cards.serializers`: Data serialization
- Used by: Frontend applications, API clients

## Practical Code Examples

### Example 1: API Request to Get Credit Cards
Making requests to the credit card API endpoints.

```python
# HTTP GET /api/cards/
# Returns paginated list of credit cards
{
    "count": 150,
    "results": [
        {
            "id": 1,
            "name": "Chase Sapphire Preferred", 
            "issuer": "Chase",
            "annual_fee": "95.00",
            "primary_reward_type": "Travel Points"
        }
    ]
}

# HTTP GET /api/cards/search/?issuer=Chase&annual_fee_max=100
# Search for Chase cards with annual fee under $100
```

### Example 2: User Profile Management
Managing user spending profiles via API.

```python
# HTTP POST /api/user-profile/
# Create or update user spending profile
{
    "spending_amounts": [
        {"category": "Groceries", "amount": "500.00"},
        {"category": "Gas", "amount": "200.00"},
        {"category": "Dining", "amount": "300.00"}
    ]
}

# HTTP GET /api/quick-recommendation/
# Get quick card recommendations based on user profile
{
    "recommendations": [
        {
            "card": "Chase Sapphire Preferred",
            "score": 85.5,
            "reason": "High travel rewards match your spending"
        }
    ]
}
```

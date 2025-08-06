# views.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `users/views.py` module, which implements Django REST Framework views for user authentication, profile management, and user-related API endpoints. The module provides comprehensive user account management including profile updates, card collection tracking, spending data management, and bulk user data operations for both authenticated and session-based users.

## Module Overview
`users/views.py` is a 230-line Django REST Framework views module that implements the complete user management API for the credit card platform. It includes class-based views for CRUD operations and function-based API views for specialized user data operations, with support for both authenticated users and anonymous session-based users.

### Key Responsibilities:
- **User Profile & Preferences Management**: Handles UserProfileView and UserPreferencesView for retrieving and updating user profile information, preferences, and settings
- **Card Collection Management**: Provides UserCardListView, UserCardDetailView, and specialized endpoints for adding, updating, and removing cards from user collections with detailed tracking
- **Bulk Data Operations**: Implements user_data_view for efficient bulk get/save operations of user spending data, card collections, and preferences in single API calls

## Initialization
These Django views are automatically registered via URL routing. No manual initialization required.

```python
# Automatically initialized by Django via users/urls.py
# Access via HTTP requests to mapped URLs:
# GET /api/users/status/ -> user_status_view
# GET /api/users/profile/ -> UserProfileView
# POST /api/users/cards/ -> UserCardListView
```

## Public API documentation

### Class-Based Views (DRF)
- **`UserProfileView`**: Get/update user profile data with credit card preferences
- **`UserPreferencesView`**: Manage user UI preferences and notification settings
- **`UserCardListView`**: List and manage user's credit card collection
- **`UserCardDetailView`**: Detailed view/management of specific user cards
- **`UserSpendingListView`**: Manage user spending profiles and amounts

### Function-Based Views
- **`user_status_view`**: Check user authentication status and basic info
- **`toggle_user_card`**: Add/remove cards from user's collection
- **`update_user_card_details`**: Update user-specific card information
- **`get_user_cards_details`**: Retrieve detailed user card collection data
- **`user_data_view`**: Bulk user data operations (get/save all user data)

### Authentication & Permissions
Most views require authentication and operate on the current user's data with proper permission checking.

## Dependencies
### External Dependencies:
- `django.shortcuts`: Django view utilities
- `rest_framework`: Django REST Framework
- `django.contrib.auth.decorators`: Authentication decorators
- `django.views.decorators.csrf`: CSRF protection

### Internal Dependencies:
- `users.models`: UserProfile, UserPreferences models
- `users.serializers`: All user-related serializers
- `cards.models`: CreditCard for user card relationships
- Used by: Frontend applications, user account management

## Practical Code Examples

### Example 1: User Profile API Operations
Managing user profiles through the API endpoints.

```python
# HTTP GET /api/users/profile/
# Returns user profile data
{
    "preferred_issuer": "Chase",
    "preferred_reward_type": "Travel Points",
    "max_annual_fee": "150.00",
    "credit_score_range": "750-850"
}

# HTTP PUT /api/users/profile/
# Update user profile
{
    "preferred_issuer": "American Express",
    "max_annual_fee": "200.00",
    "preferred_reward_type": "Cash Back"
}
```

### Example 2: User Card Collection Management
Managing user's credit card collection via API.

```python
# HTTP GET /api/users/cards/
# Returns user's card collection
{
    "count": 3,
    "results": [
        {
            "card": {
                "id": 1,
                "name": "Chase Sapphire Preferred",
                "issuer": "Chase"
            },
            "date_added": "2024-01-15",
            "is_primary": true
        }
    ]
}

# HTTP POST /api/users/cards/toggle/
# Add or remove card from collection
{
    "card_id": 5,
    "action": "add"  # or "remove"
}

# HTTP GET /api/users/data/
# Bulk user data (profile + cards + spending + preferences)
{
    "profile": {...},
    "cards": [...],
    "spending": [...],
    "preferences": {...}
}
```

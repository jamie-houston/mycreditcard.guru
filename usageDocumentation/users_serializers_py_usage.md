# serializers.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `users/serializers.py` module, which contains Django REST Framework serializers for user data serialization and API response formatting. These serializers handle user profiles, preferences, card collections, spending data, and bulk user data operations with comprehensive validation and nested relationship management.

## Module Overview
`users/serializers.py` is a 140-line Django REST Framework serializers module that provides data transformation layers for user-related models. It includes serializers for user profiles, card collections, spending data, preferences, and specialized bulk data operations for efficient API interactions.

### Key Responsibilities:
- **User Data Serialization**: Handles UserSerializer, UserProfileSerializer, and UserPreferencesSerializer for converting user models to JSON with proper field selection and validation
- **Card Collection Management**: Implements UserCardSerializer with nested CreditCardListSerializer for managing user card collections with card details and ownership tracking
- **Bulk Data Operations**: Provides UserDataSerializer for efficient bulk get/save operations of user spending, cards, and preferences in single API calls with comprehensive validation

## Initialization
Django REST Framework serializers are automatically instantiated by DRF views. No manual initialization required.

```python
# Automatically used by DRF views
# Can be instantiated manually for data operations:
from users.serializers import UserDataSerializer

serializer = UserDataSerializer(data=user_data)
if serializer.is_valid():
    result = serializer.save()
```

## Public API documentation

### Primary Serializers
- **`UserSerializer`**: Basic user data (username, email, first_name, last_name)
- **`UserProfileSerializer`**: Extended user profile with credit card preferences
- **`UserPreferencesSerializer`**: UI preferences, filters, and notification settings
- **`UserCardSerializer`**: User's card collection with nested card details
- **`UserSpendingSerializer`**: User spending data by category
- **`UserDataSerializer`**: Comprehensive bulk data operations (get/save all user data)

### Nested Relationships
- `UserCardSerializer` includes nested `CreditCardListSerializer` for complete card details
- `UserDataSerializer` combines spending, cards, and preferences in single API calls
- Complex validation ensures data consistency across related models

### Bulk Operations
`UserDataSerializer` provides efficient bulk get/save operations for entire user dataset in single API calls.

## Dependencies
### External Dependencies:
- `rest_framework.serializers`: DRF serialization framework
- `django.contrib.auth.models.User`: Django user model
- `decimal.Decimal`: Financial precision

### Internal Dependencies:
- `users.models`: UserProfile, UserPreferences models
- `cards.serializers`: CreditCardListSerializer for nested card data
- Used by: `users.views`, user API endpoints
- Used by: `roadmaps.serializers` for user context in recommendations

## Practical Code Examples

### Example 1: User Profile Management via API
How user profile data is handled through serializers.

```python
from users.serializers import UserProfileSerializer

# Update user profile via API
profile_data = {
    "preferred_issuer": "Chase",
    "preferred_reward_type": "Travel Points", 
    "max_annual_fee": "150.00",
    "credit_score_range": "750-850"
}

serializer = UserProfileSerializer(instance=user.profile, data=profile_data)
if serializer.is_valid():
    profile = serializer.save()
    
# Resulting JSON for API response:
{
    "preferred_issuer": "Chase",
    "preferred_reward_type": "Travel Points",
    "max_annual_fee": "150.00", 
    "credit_score_range": "750-850"
}
```

### Example 2: Bulk User Data Operations
Efficient bulk operations for complete user dataset.

```python
from users.serializers import UserDataSerializer

# Get all user data in single API call
serializer = UserDataSerializer(instance=request.user)
user_data = serializer.data

# Returns comprehensive user data:
{
    "user": {"username": "john_doe", "email": "john@example.com"},
    "spending": [
        {"category": "Groceries", "amount": "500.00"},
        {"category": "Gas", "amount": "200.00"}
    ],
    "cards": [
        {"card_name": "Chase Sapphire Preferred", "date_added": "2024-01-15"}
    ],
    "preferences": {
        "theme": "dark",
        "email_notifications": true
    }
}

# Save bulk data in single operation
bulk_serializer = UserDataSerializer(data=updated_data)
if bulk_serializer.is_valid():
    bulk_serializer.save(user=request.user)
```

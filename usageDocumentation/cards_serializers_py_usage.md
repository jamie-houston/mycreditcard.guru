# serializers.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/serializers.py` module, which contains Django REST Framework serializers for data transformation and validation in the credit card recommendation system. These serializers handle the conversion between Django models and JSON for API responses/requests, including complex nested relationships, read-only properties, and bulk data operations.

## Module Overview
`cards/serializers.py` is a 217-line Django REST Framework serializers module that defines data transformation layers for all major models in the cards application. It includes serializers for reference data, credit cards with complex relationships, user profiles, and specialized serializers for different API use cases.

### Key Responsibilities:
- **Model-to-JSON Conversion**: Transforms Django model instances into JSON representations for API responses with proper field selection and relationship handling
- **Request Data Validation**: Validates and deserializes incoming JSON data for API requests with comprehensive field validation and error handling  
- **Complex Relationship Management**: Handles nested serializers for reward categories, card credits, user spending amounts, and other complex model relationships

## Initialization
Django REST Framework serializers are automatically instantiated by DRF views. No manual initialization required.

```python
# Automatically used by DRF views
# Can be instantiated manually for testing:
from cards.serializers import CreditCardListSerializer

serializer = CreditCardListSerializer(data=card_data)
if serializer.is_valid():
    card = serializer.save()
```

## Public API documentation

### Primary Serializers
- **`IssuerSerializer`**: Serializes issuer data with name and card count
- **`RewardTypeSerializer`**: Handles reward type data (Cash Back, Travel Points, etc.)
- **`SpendingCategorySerializer`**: Serializes spending categories with metadata
- **`CreditCardListSerializer`**: Comprehensive card serialization with nested relationships
- **`CreditCardDetailSerializer`**: Detailed card view with all relationships
- **`RewardCategorySerializer`**: Handles reward rate data by category
- **`CreditTypeSerializer`**: Serializes spending credit types
- **`CardCreditSerializer`**: Links cards to available spending credits
- **`UserSpendingProfileSerializer`**: User spending data with nested amounts
- **`SpendingAmountSerializer`**: Individual spending amounts by category

### Nested Relationships
Serializers handle complex relationships like cards with reward categories, user profiles with spending amounts, and card collections with user preferences.

## Dependencies
### External Dependencies:
- `rest_framework.serializers`: DRF serialization framework
- `django.contrib.auth.models.User`: User authentication
- `decimal.Decimal`: Financial precision

### Internal Dependencies:
- `cards.models`: All card-related models
- Used by: `cards.views`, API endpoints
- Used by: `roadmaps.serializers` for recommendation data

## Practical Code Examples

### Example 1: Card Data Serialization for API Response
How card data is serialized for API responses.

```python
from cards.serializers import CreditCardListSerializer
from cards.models import CreditCard

# Get cards and serialize for API response
cards = CreditCard.objects.prefetch_related('reward_categories')
serializer = CreditCardListSerializer(cards, many=True)

# Resulting JSON structure:
{
    "id": 1,
    "name": "Chase Sapphire Preferred",
    "issuer": "Chase",
    "annual_fee": "95.00",
    "primary_reward_type": "Travel Points",
    "reward_categories": [
        {
            "spending_category": "Travel",
            "reward_rate": "2.0",
            "reward_type": "Travel Points"
        }
    ]
}
```

### Example 2: User Spending Profile Serialization
Managing user spending data through serializers.

```python
from cards.serializers import UserSpendingProfileSerializer

# Create spending profile via serializer
profile_data = {
    "spending_amounts": [
        {"category": 1, "amount": "500.00"},  # Groceries
        {"category": 2, "amount": "200.00"},  # Gas
        {"category": 3, "amount": "300.00"}   # Dining
    ]
}

serializer = UserSpendingProfileSerializer(data=profile_data)
if serializer.is_valid():
    profile = serializer.save(user=request.user)
    
# Validates amounts, creates nested relationships
# Returns structured profile data for API responses
```

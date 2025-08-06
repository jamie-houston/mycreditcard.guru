# models.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `users/models.py` module, which defines extended user profile models for the users app. These models store additional user-specific data beyond Django's default User model, including user preferences like preferred issuer, reward type, maximum annual fee, and UI settings for personalized experiences.

## Module Overview
`users/models.py` is a 47-line Django models module that extends Django's built-in User model with additional profile and preferences data. It includes UserProfile for storing user preferences and UserPreferences for saved filter preferences and UI settings.

### Key Responsibilities:
- **Extended User Profiles**: Defines UserProfile model with OneToOneField to User for storing credit card preferences like preferred issuer, reward type, and maximum annual fee
- **User Preferences Management**: Implements UserPreferences model for storing saved filter preferences, UI theme settings, and email notification preferences
- **Personalization Data**: Provides structured storage for user-specific customization options that enhance the credit card recommendation experience

## Initialization
These Django models are automatically initialized by Django's ORM. No manual initialization required.

```python
# Models are automatically registered by Django
# Access via Django ORM:
from users.models import UserProfile, UserPreferences
from django.contrib.auth.models import User

# Create user profile
user = User.objects.get(username="john_doe")
profile = UserProfile.objects.create(
    user=user,
    preferred_issuer="Chase",
    max_annual_fee=150.00
)
```

## Public API documentation

### Primary Models
- **`UserProfile`**: Extended user profile with OneToOneField to User, storing credit card preferences like preferred issuer, reward type, and maximum annual fee tolerance
- **`UserPreferences`**: User interface and notification preferences including theme settings, saved filter preferences, and email notification options

### Key Model Properties
- `UserProfile` includes fields for credit card preferences, spending limits, and personalization data
- `UserPreferences` manages UI settings, notification preferences, and saved filter configurations
- Both models include Django's standard timestamp fields (created_at, updated_at)

### Relationships
- `UserProfile` has OneToOneField relationship with Django's User model
- `UserPreferences` also links to User for managing UI and notification settings
- Models support the broader credit card recommendation and roadmap functionality

## Dependencies
### External Dependencies:
- `django.db.models`: Django ORM functionality
- `django.contrib.auth.models.User`: Django user authentication
- `decimal.Decimal`: Precise financial calculations

### Internal Dependencies:
- Referenced by: `users.views`, `users.serializers`, `users.admin`
- Used by: `roadmaps.recommendation_engine` for user preference context
- Used by: `cards.views` for personalized recommendations

## Practical Code Examples

### Example 1: Creating User Profile with Preferences
Setting up a complete user profile for credit card recommendations.

```python
from users.models import UserProfile, UserPreferences
from django.contrib.auth.models import User
from decimal import Decimal

# Get or create user
user = User.objects.create_user(
    username="jane_doe",
    email="jane@example.com",
    first_name="Jane",
    last_name="Doe"
)

# Create user profile with credit card preferences
profile = UserProfile.objects.create(
    user=user,
    preferred_issuer="Chase",
    preferred_reward_type="Travel Points",
    max_annual_fee=Decimal("200.00"),
    credit_score_range="750-850"
)

# Create user preferences for UI and notifications
preferences = UserPreferences.objects.create(
    user=user,
    theme="dark",
    email_notifications=True,
    push_notifications=False,
    saved_filters='{"max_fee": 150, "issuer": "Chase"}'
)
```

### Example 2: Retrieving User Data for Recommendations
Example of accessing user profile data for personalized recommendations.

```python
from users.models import UserProfile, UserPreferences

def get_user_context(user):
    """Get complete user context for recommendations"""
    try:
        profile = UserProfile.objects.get(user=user)
        preferences = UserPreferences.objects.get(user=user)
        
        return {
            "preferred_issuer": profile.preferred_issuer,
            "preferred_reward_type": profile.preferred_reward_type,
            "max_annual_fee": profile.max_annual_fee,
            "credit_score_range": profile.credit_score_range,
            "ui_theme": preferences.theme,
            "notifications_enabled": preferences.email_notifications
        }
    except (UserProfile.DoesNotExist, UserPreferences.DoesNotExist):
        return None

# Usage in recommendation engine
user_context = get_user_context(request.user)
if user_context:
    # Use preferences to filter recommendations
    max_fee = user_context["max_annual_fee"]
    preferred_issuer = user_context["preferred_issuer"]
```

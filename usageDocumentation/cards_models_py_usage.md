# models.py Usage Documentation

## Executive Summary
This document provides usage documentation for the Django models in the cards application, which defines the complete database schema for a credit card recommendation system. These models handle credit card data, issuer information, reward systems, user spending profiles, and complex relationships between cards and their benefits, providing the foundation for personalized credit card recommendations.

## Module Overview
`cards/models.py` contains the core Django model classes that define the database schema for a sophisticated credit card recommendation platform. This module implements a comprehensive credit card ecosystem with support for multiple card types, complex reward structures, spending category hierarchies, and user preference tracking.

### Key Responsibilities:
- **Credit Card Data Management**: Defines CreditCard, Issuer, and RewardType models with complete card information including fees, bonuses, and metadata
- **Reward System Architecture**: Implements RewardCategory, CardCredit, CreditType, and SpendingCredit models for complex reward rate calculations and credit benefit tracking
- **User Profile & Preferences**: Manages UserSpendingProfile, SpendingAmount, and preference models for personalized recommendations based on spending patterns
- **Spending Category Hierarchy**: Provides SpendingCategory model with parent-child relationships for flexible categorization of expenses
- **Card Ownership Tracking**: Handles UserCard model for tracking user-owned cards with dates, nicknames, and status information


## Django Models Overview
This module contains 10 primary Django model classes:

**Core Models:**
- `Issuer` - Credit card issuing banks/companies
- `CreditCard` - Main credit card model with fees, bonuses, metadata
- `RewardType` - Types of rewards (points, miles, cashback, hotel_nights)

**Reward & Credit System:**
- `RewardCategory` - Card-specific reward rates per spending category
- `CreditType` - Types of card credits/benefits
- `SpendingCredit` - Specific spending credits (airline fee credits, etc.)
- `CardCredit` - Credits available on specific cards

**User & Preference System:**
- `UserSpendingProfile` - User spending profiles with privacy controls
- `SpendingAmount` - User spending amounts per category
- `UserCard` - User-owned cards with tracking details
- `UserCreditPreference` & `UserSpendingCreditPreference` - User credit value preferences

**Category System:**
- `SpendingCategory` - Hierarchical spending categories with parent-child relationships

## Public API documentation

### Model Classes
Provides Django ORM models for credit card system data management.

#### Core Models:
- **CreditCard**: Represents individual credit card products with features, rewards, and terms
- **Issuer**: Bank or financial institution that issues credit cards
- **RewardType**: Types of rewards offered (cashback, points, miles, etc.)
- **SpendingCategory**: Categories for reward multipliers (dining, travel, gas, etc.)
- **UserSpendingProfile**: User's spending patterns and preferences for recommendations

## Dependencies

**External Dependencies:**
- `django.db.models` - Django ORM base classes and field types
- `django.contrib.auth.models.User` - Django built-in User model for authentication
- `django.core.validators` - MinValueValidator, MaxValueValidator for field validation
- `json` - Standard library for JSON metadata handling

**Internal Dependencies:**
- Self-referential relationships within models (SpendingCategory parent-child, etc.)
- Foreign key relationships between all major models (CreditCard -> Issuer, RewardCategory -> CreditCard, etc.)

**Used by:**
- Django admin interface for card management
- Django REST API serializers and views
- Card recommendation algorithms
- User preference and spending analysis systems

## Practical Code Examples

### Example 1: Creating a Credit Card with Reward Categories
Creating a new credit card with complex reward structure and credit benefits.

```python
# Create issuer and reward types
chase = Issuer.objects.create(name="Chase", slug="chase")
points = RewardType.objects.create(name="points", slug="points")

# Create credit card
sapphire = CreditCard.objects.create(
    name="Sapphire Preferred",
    slug="sapphire-preferred",
    issuer=chase,
    annual_fee=95.00,
    signup_bonus_amount=60000,
    signup_bonus_type=points,
    primary_reward_type=points
)

# Add reward categories
dining_category = SpendingCategory.objects.get(slug="dining")
RewardCategory.objects.create(
    card=sapphire,
    category=dining_category,
    reward_rate=2.00,
    reward_type=points
)
```

### Example 2: User Profile with Spending Tracking
Setting up a user spending profile with category-based spending amounts and preferences.

```python
# Create user profile
profile = UserSpendingProfile.objects.create(
    user=request.user,
    privacy_setting='private'
)

# Add monthly spending amounts
dining = SpendingCategory.objects.get(slug="dining")
SpendingAmount.objects.create(
    profile=profile,
    category=dining,
    monthly_amount=800.00
)

# Track user's credit preferences
airline_credit = CreditType.objects.get(slug="airline-fee-credit")
UserCreditPreference.objects.create(
    profile=profile,
    credit_type=airline_credit,
    values_credit=True
)
```


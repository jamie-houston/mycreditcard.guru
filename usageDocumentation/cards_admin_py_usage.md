# admin.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `cards/admin.py` module, which configures the Django admin interface for various models within the cards app. This module provides comprehensive administrative functionality with inline editing, custom displays, filtering, and search capabilities for managing credit card data, user profiles, and related models.

## Module Overview
`cards/admin.py` is an 87-line Django admin configuration module that customizes the administrative interface for the cards application. It uses @admin.register decorators and inline classes to provide efficient management of credit card data and user information through Django's admin interface.

### Key Responsibilities:
- **Model Admin Registration**: Registers and configures admin interfaces for Issuer, RewardType, SpendingCategory, CreditCard, RewardCategory, CreditType, CardCredit, and UserSpendingProfile models
- **Inline Editing Setup**: Defines TabularInline and StackedInline classes for RewardCategory, CardCredit, SpendingAmount, and UserCreditPreference to manage related objects within parent forms
- **Admin Interface Customization**: Provides list displays, filters, search fields, and custom admin functionality for efficient data management and administrative workflows

## Initialization
Django admin configurations are automatically registered when Django starts. No manual initialization required.

```python
# Automatically registered via @admin.register decorators
# Access via Django admin interface at /admin/
# Models become available in admin interface automatically
```

## Public API documentation

### Registered Model Admins
- **`IssuerAdmin`**: Manages credit card issuers with list display and search
- **`RewardTypeAdmin`**: Handles reward types with basic CRUD operations
- **`SpendingCategoryAdmin`**: Manages spending categories with filtering
- **`CreditCardAdmin`**: Comprehensive card management with inline reward categories
- **`CreditTypeAdmin`**: Manages spending credit types
- **`UserSpendingProfileAdmin`**: User spending profiles with inline spending amounts

### Inline Admin Classes
- **`RewardCategoryInline`**: TabularInline for managing reward categories within cards
- **`CardCreditInline`**: StackedInline for card spending credits
- **`SpendingAmountInline`**: TabularInline for spending amounts within profiles
- **`UserCreditPreferenceInline`**: Inline for user credit preferences

### Admin Features
- List displays with relevant fields for quick overview
- Search functionality on key fields like names and descriptions
- Filtering options for efficient data management
- Inline editing for related objects

## Dependencies
### External Dependencies:
- `django.contrib.admin`: Django admin framework
- `django.contrib.auth.admin`: User admin integration

### Internal Dependencies:
- `cards.models`: All card-related models being administered
- Used by: Django admin interface, staff users, data management

## Practical Code Examples

### Example 1: Accessing Admin Interface
Using the Django admin interface for data management.

```python
# Navigate to /admin/ in browser
# Login with superuser credentials
# Access cards section to manage:

# Issuers - Add/edit credit card issuers
# Credit Cards - Comprehensive card management with inline rewards
# Reward Types - Manage reward categories
# Spending Categories - Configure spending types
# User Spending Profiles - View user spending data
```

### Example 2: Inline Editing in Admin
How inline editing works for related objects.

```python
# In CreditCardAdmin, when editing a card:
# - RewardCategoryInline allows editing reward rates directly
# - CardCreditInline shows available spending credits
# - All related data editable in single form

# Example: Editing Chase Sapphire Preferred
# Card details: name, issuer, annual fee, etc.
# Inline reward categories:
#   - Travel: 2x points
#   - Dining: 2x points
#   - General: 1x points
# Inline card credits:
#   - Signup bonus: 60,000 points
#   - Annual travel credit: $300
```

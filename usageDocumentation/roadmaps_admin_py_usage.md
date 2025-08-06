# admin.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `roadmaps/admin.py` module, which configures the Django admin interface for roadmap-related models. This module provides comprehensive administrative functionality with inline editing, custom displays, filtering, and search capabilities for managing roadmap filters, roadmaps, recommendations, and calculation data.

## Module Overview
`roadmaps/admin.py` is a 43-line Django admin configuration module that customizes the administrative interface for the roadmaps application. It uses @admin.register decorators and inline classes to provide efficient management of roadmap data through Django's admin interface.

### Key Responsibilities:
- **Roadmap Model Administration**: Registers and configures admin interfaces for RoadmapFilter, Roadmap, RoadmapRecommendation, and RoadmapCalculation models with proper list displays and filtering
- **Inline Editing Configuration**: Defines TabularInline and StackedInline classes for RoadmapRecommendation and RoadmapCalculation to manage related objects within parent roadmap forms
- **Search & Filter Setup**: Provides search fields, list filters, and custom admin functionality for efficient roadmap data management and administrative workflows

## Initialization
Django admin configurations are automatically registered when Django starts. No manual initialization required.

```python
# Automatically registered via @admin.register decorators
# Access via Django admin interface at /admin/
# Roadmap models become available in admin interface automatically
```

## Public API documentation

### Registered Model Admins
- **`RoadmapFilterAdmin`**: Manages roadmap filter configurations with display options
- **`RoadmapAdmin`**: Comprehensive roadmap management with inline recommendations and calculations
- **`RoadmapRecommendationAdmin`**: Individual recommendation management with filtering
- **`RoadmapCalculationAdmin`**: Detailed calculation data and metrics management

### Inline Admin Classes
- **`RoadmapRecommendationInline`**: TabularInline for managing recommendations within roadmaps
- **`RoadmapCalculationInline`**: StackedInline for detailed calculation data within recommendations

### Admin Features
- List displays showing roadmap names, users, creation dates, and status
- Search functionality on roadmap names and user information
- Filtering by creation date, user, and recommendation status
- Inline editing for recommendations and calculations within roadmaps

## Dependencies
### External Dependencies:
- `django.contrib.admin`: Django admin framework
- `django.contrib.auth.admin`: User admin integration

### Internal Dependencies:
- `roadmaps.models`: All roadmap-related models being administered
- Used by: Django admin interface, staff users, roadmap data management

## Practical Code Examples

### Example 1: Managing Roadmaps in Admin
Using the Django admin interface for roadmap data management.

```python
# Navigate to /admin/ in browser
# Login with superuser credentials
# Access roadmaps section to manage:

# Roadmap Filters - Configure filter templates
# Roadmaps - Comprehensive roadmap management
# Roadmap Recommendations - Individual recommendation oversight
# Roadmap Calculations - Detailed calculation review
```

### Example 2: Inline Roadmap Management
How inline editing works for roadmap recommendations.

```python
# In RoadmapAdmin, when editing a roadmap:
# - RoadmapRecommendationInline shows all recommendations
# - RoadmapCalculationInline shows calculation details
# - Full roadmap data editable in single interface

# Example: Editing "Travel Enthusiast Strategy" roadmap
# Roadmap details: name, user, filters, description
# Inline recommendations:
#   - Chase Sapphire Preferred: Score 87.5
#   - Chase Sapphire Reserve: Score 84.2
#   - Amex Gold Card: Score 79.8
# Inline calculations:
#   - Annual values, payback periods, bonus calculations
```

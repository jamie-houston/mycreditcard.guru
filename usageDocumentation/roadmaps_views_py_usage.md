# views.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `roadmaps/views.py` module, which implements Django REST Framework views for managing recommendation roadmaps. These views handle roadmap CRUD operations, filter management, and integration with the RecommendationEngine for generating user-specific credit card recommendations with support for both authenticated and session-based users.

## Module Overview
`roadmaps/views.py` is a 247-line Django REST Framework views module that provides the API endpoints for the roadmap feature. It includes class-based views for roadmap management and function-based API views for creating roadmaps and generating recommendations with complex user/session handling.

### Key Responsibilities:  
- **Roadmap CRUD Operations**: Provides RoadmapListView and RoadmapDetailView for creating, retrieving, updating, and deleting user roadmaps with proper user/session access control
- **Filter Management**: Implements RoadmapFilterListView for managing available roadmap filters and filter combinations for recommendation customization
- **Recommendation Generation**: Handles create_roadmap_view and generate_roadmap_view for creating roadmaps with filters and generating recommendations using the RecommendationEngine

## Initialization
These Django views are automatically registered via URL routing. No manual initialization required.

```python
# Automatically initialized by Django via roadmaps/urls.py
# Access via HTTP requests to mapped URLs:
# GET /api/roadmaps/ -> RoadmapListView
# POST /api/roadmaps/create/ -> create_roadmap_view
# POST /api/roadmaps/{id}/generate/ -> generate_roadmap_view
```

## Public API documentation

### Class-Based Views (DRF)
- **`RoadmapFilterListView`**: List available roadmap filter options
- **`RoadmapListView`**: List user's roadmaps with filtering and pagination
- **`RoadmapDetailView`**: Get detailed roadmap with recommendations and calculations

### Function-Based Views
- **`create_roadmap_view`**: Create new roadmap with filters and user context
- **`generate_roadmap_view`**: Generate recommendations for existing roadmap
- **`quick_recommendation_view`**: Get quick card recommendations without saving
- **`roadmap_stats_view`**: Get roadmap statistics and analytics
- **`export_scenario_view`**: Export roadmap data for testing/debugging

### Recommendation Engine Integration
Views integrate with the sophisticated recommendation engine to generate personalized credit card strategies based on user preferences and spending patterns.

## Dependencies
### External Dependencies:
- `django.shortcuts`: Django view utilities
- `rest_framework`: Django REST Framework
- `django.contrib.auth.decorators`: Authentication decorators
- `django.http`: HTTP response handling

### Internal Dependencies:
- `roadmaps.models`: All roadmap-related models
- `roadmaps.serializers`: Roadmap data serialization
- `roadmaps.recommendation_engine`: Core recommendation logic
- `cards.models`: Credit card data for recommendations
- Used by: Frontend applications, roadmap management interfaces

## Practical Code Examples

### Example 1: Creating and Generating a Roadmap
Complete roadmap creation and recommendation generation workflow.

```python
# HTTP POST /api/roadmaps/create/
# Create new roadmap with filters
{
    "name": "Travel Rewards Strategy",
    "filters": {
        "max_annual_fee": "150.00",
        "preferred_issuer": "Chase",
        "preferred_reward_type": "Travel Points",
        "max_cards": 3
    },
    "user_spending": [
        {"category": "Travel", "amount": "800.00"},
        {"category": "Dining", "amount": "400.00"}
    ]
}

# HTTP POST /api/roadmaps/5/generate/
# Generate recommendations for roadmap ID 5
{
    "updated_spending": [
        {"category": "Travel", "amount": "1000.00"}
    ],
    "updated_preferences": {
        "max_annual_fee": "200.00"
    }
}

# Returns generated recommendations:
{
    "roadmap_id": 5,
    "recommendations": [
        {
            "card_name": "Chase Sapphire Preferred",
            "score": 87.5,
            "annual_fee": "95.00",
            "reasoning": "High travel rewards, excellent transfer partners",
            "estimated_annual_value": "420.00"
        }
    ]
}
```

### Example 2: Quick Recommendations Without Saving
Getting instant recommendations for comparison.

```python
# HTTP POST /api/roadmaps/quick-recommendation/
# Get quick recommendations without creating roadmap
{
    "spending_profile": [
        {"category": "Groceries", "amount": "500.00"},
        {"category": "Gas", "amount": "200.00"}
    ],
    "preferences": {
        "max_annual_fee": "100.00",
        "preferred_reward_type": "Cash Back"
    }
}

# Returns immediate recommendations:
{
    "recommendations": [
        {
            "card_name": "Chase Freedom Unlimited",
            "score": 82.3,
            "match_reasoning": "Strong cash back for everyday spending",
            "annual_value": "185.00"
        }
    ],
    "total_estimated_value": "185.00"
}
```

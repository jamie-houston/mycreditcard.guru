# models.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `roadmaps/models.py` module, which defines Django models for the recommendation roadmap feature. These models store user-specific recommendation plans, filters, individual card recommendations, and detailed calculation data for portfolio optimization and recommendation tracking.

## Module Overview
`roadmaps/models.py` is a 72-line Django models module that implements the data structures for saving and managing user recommendation roadmaps. It includes models for roadmap filters, roadmaps themselves, individual recommendations within roadmaps, and calculation results for recommendation analysis.

### Key Responsibilities:
- **Roadmap Management**: Defines Roadmap and RoadmapFilter models for storing user recommendation preferences, filter criteria, and roadmap configurations
- **Recommendation Storage**: Implements RoadmapRecommendation model for storing individual card recommendations with actions, priorities, estimated rewards, and reasoning
- **Calculation Tracking**: Provides RoadmapCalculation model for storing detailed recommendation calculation data and results for analysis and auditing

## Initialization
These Django models are automatically initialized by Django's ORM. No manual initialization required.

```python
# Models are automatically registered by Django
# Access via Django ORM:
from roadmaps.models import Roadmap, RoadmapFilter, RoadmapRecommendation

# Create roadmap with filters
roadmap = Roadmap.objects.create(
    name="Travel Enthusiast Plan",
    user=user_obj
)
```

## Public API documentation

### Primary Models
- **`RoadmapFilter`**: Defines filtering criteria for roadmap generation (issuer preferences, fee limits, reward types)
- **`Roadmap`**: Main roadmap model linking users to personalized credit card strategies with metadata
- **`RoadmapRecommendation`**: Individual card recommendations within a roadmap with scores and reasoning
- **`RoadmapCalculation`**: Detailed calculation data and metrics for each recommendation

### Key Model Properties
All models include Django's standard fields (id, created_at, updated_at) plus roadmap-specific fields for comprehensive recommendation tracking and personalization.

### Relationships
- `Roadmap` links to User and contains multiple `RoadmapRecommendation` objects
- `RoadmapRecommendation` includes detailed card data and links to `RoadmapCalculation` for metrics
- `RoadmapFilter` provides reusable filter configurations for roadmap generation

## Dependencies
### External Dependencies:
- `django.db.models`: Django ORM functionality
- `django.contrib.auth.models.User`: Django user authentication
- `decimal.Decimal`: Precise financial calculations
- `uuid.UUID`: Unique identifier generation

### Internal Dependencies:
- `cards.models`: CreditCard, Issuer, RewardType for foreign key relationships
- Used by: `roadmaps.views`, `roadmaps.serializers`, `roadmaps.recommendation_engine`
- Used by: API endpoints for roadmap CRUD operations

## Practical Code Examples

### Example 1: Creating a Roadmap with Filters
Complete example of setting up a personalized roadmap.

```python
from roadmaps.models import Roadmap, RoadmapFilter, RoadmapRecommendation
from django.contrib.auth.models import User
from decimal import Decimal

# Create user and filter
user = User.objects.get(username="john_doe")
filter_obj = RoadmapFilter.objects.create(
    max_annual_fee=Decimal("150.00"),
    preferred_issuer="Chase",
    preferred_reward_type="Travel Points",
    max_cards=3
)

# Create roadmap
roadmap = Roadmap.objects.create(
    name="Travel Rewards Strategy",
    user=user,
    roadmap_filter=filter_obj,
    description="Optimized for travel spending and signup bonuses"
)

# Add recommendations
recommendation = RoadmapRecommendation.objects.create(
    roadmap=roadmap,
    card_name="Chase Sapphire Preferred",
    card_issuer="Chase",
    annual_fee=Decimal("95.00"),
    recommendation_score=Decimal("87.5"),
    reasoning="High travel rewards, transfer partners"
)
```

### Example 2: Querying Roadmap Data for API
Example of retrieving roadmap data with related calculations.

```python
from roadmaps.models import Roadmap

# Get user's roadmaps with full related data
user_roadmaps = Roadmap.objects.filter(user=request.user).prefetch_related(
    'recommendations',
    'recommendations__calculations'
)

for roadmap in user_roadmaps:
    print(f"Roadmap: {roadmap.name}")
    for rec in roadmap.recommendations.all():
        print(f"  Card: {rec.card_name} (Score: {rec.recommendation_score})")
        if hasattr(rec, 'calculations'):
            calc = rec.calculations
            print(f"    Annual Value: ${calc.estimated_annual_value}")
            print(f"    Payback Period: {calc.payback_period_months} months")
```

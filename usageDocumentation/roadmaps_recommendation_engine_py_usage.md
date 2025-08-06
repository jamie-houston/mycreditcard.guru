# recommendation_engine.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `recommendation_engine.py` module, which contains the core recommendation engine for the credit card platform. The RecommendationEngine class analyzes user spending patterns, issuer policies (like Chase's 5/24 rule), reward optimization, and annual fee vs. benefits analysis to generate portfolio-optimized credit card recommendations with sophisticated fallback strategies.

## Module Overview
`recommendation_engine.py` is a comprehensive recommendation service class that implements the core business logic for personalized credit card recommendations. This 1,822-line module contains sophisticated algorithms for portfolio optimization, issuer policy compliance, reward value calculations, and complex decision trees for apply/keep/cancel recommendations.

### Key Responsibilities:
- **Portfolio Optimization**: Analyzes user spending patterns across categories and recommends optimal card combinations to maximize rewards while minimizing fees
- **Issuer Policy Compliance**: Implements and enforces issuer-specific policies like Chase's 5/24 rule, application velocity limits, and relationship banking requirements  
- **Reward Value Analysis**: Calculates complex reward rates, signup bonus values, annual fee justifications, and long-term value projections for each card recommendation
- **Fallback Strategy Implementation**: Provides intelligent fallbacks for edge cases, low spending scenarios, and when primary recommendations don't meet quality thresholds



## Initialization
The RecommendationEngine is initialized with a UserSpendingProfile and optional user cards data for session-based users.

```python
from roadmaps.recommendation_engine import RecommendationEngine
from cards.models import UserSpendingProfile

# For authenticated users
profile = UserSpendingProfile.objects.get(user=request.user)
engine = RecommendationEngine(profile)

# For session-based users with user cards data
user_cards_data = [
    {
        'card_id': 1,
        'opened_date': '2020-01-01',
        'is_active': True,
        'nickname': 'My Travel Card'
    }
]
engine = RecommendationEngine(profile, user_cards_data=user_cards_data)
```

## Public API documentation

### `generate_quick_recommendations(roadmap: Roadmap) -> List[dict]`
Primary method for generating credit card recommendations without saving to database.
- **Parameters**: `roadmap` - Roadmap object containing filters and preferences
- **Returns**: List of recommendation dictionaries with detailed breakdowns
- **Purpose**: Main entry point for recommendation generation with complete reward calculations

### `_get_filtered_cards(roadmap: Roadmap) -> QuerySet`
Applies roadmap filters to get eligible cards for recommendations.
- **Parameters**: `roadmap` - Roadmap with filter criteria
- **Returns**: Filtered QuerySet of CreditCard objects
- **Purpose**: Pre-filters cards based on user preferences and roadmap settings

### `_generate_portfolio_optimized_recommendations(cards, roadmap) -> List[dict]`
Core algorithm that generates optimized card portfolio recommendations.
- **Parameters**: `cards` - Eligible cards QuerySet, `roadmap` - User roadmap
- **Returns**: List of prioritized recommendations with detailed reasoning
- **Purpose**: Implements the main portfolio optimization logic with issuer policies

## Dependencies

### External Dependencies:
- **Django ORM**: Database queries and model operations
- **Python Decimal**: Precise financial calculations
- **Python DateTime**: Date handling for card applications and eligibility
- **Collections**: Data structure utilities for recommendation processing

### Internal Dependencies:
- **cards.models**: CreditCard, Issuer, RewardType, SpendingCategory models
- **roadmaps.models**: Roadmap, RoadmapFilter, RoadmapRecommendation models
- **Recommendation Logic**: Complex algorithms for portfolio optimization and issuer policy compliance

## Practical Code Examples

### Example 1: Basic Recommendation Generation
Generate recommendations for a user with spending profile and roadmap filters.

```python
from roadmaps.models import Roadmap
from roadmaps.recommendation_engine import RecommendationEngine

# Create roadmap with user preferences
roadmap = Roadmap.objects.create(
    profile=user_profile,
    name="Travel Optimization",
    max_recommendations=5
)

# Generate recommendations
engine = RecommendationEngine(user_profile)
recommendations = engine.generate_quick_recommendations(roadmap)

# Process results
for rec in recommendations:
    print(f"{rec['action'].upper()}: {rec['card'].name}")
    print(f"Estimated Value: ${rec['estimated_rewards']}")
    print(f"Reasoning: {rec['reasoning']}")
```

### Example 2: Session-Based User with Card Data
Handle recommendations for anonymous users with session data.

```python
# For users without accounts but with session card data
user_cards = request.session.get('user_cards', [])
session_profile = UserSpendingProfile.objects.get(session_key=request.session.session_key)

engine = RecommendationEngine(session_profile, user_cards_data=user_cards)
recommendations = engine.generate_quick_recommendations(roadmap)

# Engine automatically handles mock UserCard objects for consistency
for rec in recommendations:
    if rec['action'] == 'apply':
        print(f"Apply for: {rec['card'].name} - ${rec['estimated_rewards']}/year value")
```



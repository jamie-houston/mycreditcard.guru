#!/usr/bin/env python
"""
Database Column Inspector

This script checks database column definitions and schema for debugging
and validation purposes. Displays available columns and model attributes.
"""

from app import create_app
from app.models.credit_card import CreditCard

app = create_app()
with app.app_context():
    print("CreditCard columns:", CreditCard.__table__.columns.keys())
    print("Has min_credit_score:", hasattr(CreditCard, 'min_credit_score'))
    
    # Check the recommendation engine function
    try:
        from app.engine.recommendation import RecommendationEngine
        print("\nRecommendationEngine methods:", [m for m in dir(RecommendationEngine) if not m.startswith('__')])
    except Exception as e:
        print(f"Error importing RecommendationEngine: {e}") 
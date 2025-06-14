#!/usr/bin/env python3
"""Test script to verify the duplicate recommendation ID fix."""

import sys
import os
sys.path.append('./flask_app')

from flask_app.app import create_app
from flask_app.app import db
from flask_app.app.models.user_data import UserProfile
from flask_app.app.models.credit_card import CreditCard
from flask_app.app.models import CardIssuer
from flask_app.app.blueprints.recommendations.services import RecommendationService
import json

def test_duplicate_recommendation_fix():
    """Test that generating the same recommendation twice doesn't cause a UNIQUE constraint error."""
    
    app = create_app('testing')
    with app.app_context():
        # Create all tables
        db.create_all()
        
        print('🧪 Testing Duplicate Recommendation ID Fix')
        print('=' * 50)
        
        try:
            # Create a test issuer
            issuer = CardIssuer(name='Test Bank')
            db.session.add(issuer)
            db.session.commit()
            
            # Create test cards
            card1 = CreditCard(
                name='Test Card 1',
                issuer_id=issuer.id,
                annual_fee=95.0,
                point_value=0.01,
                reward_categories=json.dumps([
                    {"category": "dining", "rate": 3.0},
                    {"category": "travel", "rate": 2.0},
                    {"category": "other", "rate": 1.0}
                ]),
                signup_bonus_value=500.0
            )
            card2 = CreditCard(
                name='Test Card 2',
                issuer_id=issuer.id,
                annual_fee=0.0,
                point_value=0.01,
                reward_categories=json.dumps([
                    {"category": "groceries", "rate": 2.0},
                    {"category": "gas", "rate": 2.0},
                    {"category": "other", "rate": 1.0}
                ]),
                signup_bonus_value=200.0
            )
            db.session.add(card1)
            db.session.add(card2)
            db.session.commit()
            
            # Create a test profile
            profile = UserProfile(
                name='Test Profile',
                credit_score=750,
                income=100000.0,
                total_monthly_spend=3000.0,
                category_spending=json.dumps({
                    'dining': 500,
                    'travel': 800,
                    'groceries': 600,
                    'gas': 300,
                    'other': 800
                }),
                session_id='test-session-123'
            )
            db.session.add(profile)
            db.session.commit()
            
            print(f'✅ Created test profile with ID: {profile.id}')
            
            # Generate first recommendation
            print('📊 Generating first recommendation...')
            recommendation1 = RecommendationService.generate_recommendation(
                session_id='test-session-123',
                profile_id=profile.id
            )
            print(f'✅ First recommendation created with ID: {recommendation1.recommendation_id[:16]}...')
            
            # Generate second recommendation with same profile (should return existing one)
            print('📊 Generating second recommendation with same profile...')
            recommendation2 = RecommendationService.generate_recommendation(
                session_id='test-session-123',
                profile_id=profile.id
            )
            print(f'✅ Second recommendation returned with ID: {recommendation2.recommendation_id[:16]}...')
            
            # Check if they're the same
            if recommendation1.recommendation_id == recommendation2.recommendation_id:
                print('✅ SUCCESS: Both recommendations have the same ID (existing one was returned)')
                print('✅ No UNIQUE constraint violation occurred')
                
                # Check if they're actually the same object in the database
                if recommendation1.id == recommendation2.id:
                    print('✅ PERFECT: Same database record was returned (no duplicate created)')
                else:
                    print('⚠️  WARNING: Different database records but same recommendation_id')
                
                return True
            else:
                print('❌ FAILURE: Different recommendation IDs were generated')
                print(f'   First:  {recommendation1.recommendation_id}')
                print(f'   Second: {recommendation2.recommendation_id}')
                return False
                
        except Exception as e:
            print(f'❌ ERROR: {str(e)}')
            return False
        finally:
            # Clean up
            db.session.rollback()
            db.drop_all()

if __name__ == '__main__':
    success = test_duplicate_recommendation_fix()
    sys.exit(0 if success else 1) 
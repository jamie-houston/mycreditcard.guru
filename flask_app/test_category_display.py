#!/usr/bin/env python3
"""Test script to verify category values calculation and display."""

from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
from app.engine.recommendation import RecommendationEngine
import json

def test_category_values():
    """Test that category values are calculated correctly."""
    app = create_app()
    
    with app.app_context():
        # Get the first user profile
        profile = UserProfile.query.first()
        if not profile:
            print("❌ No user profiles found in database")
            return
        
        print(f"✅ Found profile: {profile.name}")
        print(f"📊 Category spending: {profile.get_category_spending()}")
        
        # Get all credit cards
        cards = CreditCard.query.all()
        if not cards:
            print("❌ No credit cards found in database")
            return
        
        print(f"✅ Found {len(cards)} credit cards")
        for card in cards:
            print(f"   - {card.name} (Dining: {card.dining_reward_rate}%, Travel: {card.travel_reward_rate}%)")
        
        # Generate recommendations
        try:
            recommendation_data = RecommendationEngine.generate_recommendations(profile, cards)
            print(f"✅ Generated recommendations successfully")
            print(f"📈 Total value: ${recommendation_data['total_value']:.2f}")
            print(f"💳 Recommended cards: {len(recommendation_data['recommended_sequence'])}")
            
            # Check category values for each card
            print("\n🎯 Category Values by Card:")
            for card_id in recommendation_data['recommended_sequence']:
                card_details = recommendation_data['card_details'][str(card_id)]
                card = next((c for c in cards if c.id == card_id), None)
                if card and 'category_values' in card_details:
                    print(f"\n   {card.name}:")
                    for category, value in card_details['category_values'].items():
                        if value > 0:
                            print(f"     - {category.capitalize()}: ${value:.2f}/month (${value*12:.0f}/year)")
            
            # Calculate total category values (what we'll show on the results page)
            category_totals = {}
            for card_id in recommendation_data['recommended_sequence']:
                card_details = recommendation_data['card_details'][str(card_id)]
                if 'category_values' in card_details:
                    for category, value in card_details['category_values'].items():
                        if value > 0:
                            category_totals[category] = category_totals.get(category, 0) + value
            
            print(f"\n💰 Total Category Values (what users will see):")
            for category, total_value in category_totals.items():
                print(f"   - {category.capitalize()}: ${total_value:.2f}/month (${total_value*12:.0f}/year)")
            
            if not category_totals:
                print("   ⚠️  No category-specific values found - cards may only offer base rewards")
                
        except Exception as e:
            print(f"❌ Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_category_values() 
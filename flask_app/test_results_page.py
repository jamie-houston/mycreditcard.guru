#!/usr/bin/env python3
"""Test script to simulate the results page and verify category totals calculation."""

from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
from app.engine.recommendation import RecommendationEngine

def test_results_page_logic():
    """Test the logic used in the results page route."""
    app = create_app()
    
    with app.app_context():
        # Get the first user profile
        profile = UserProfile.query.first()
        if not profile:
            print("❌ No user profiles found in database")
            return
        
        # Get all credit cards
        cards = CreditCard.query.all()
        if not cards:
            print("❌ No credit cards found in database")
            return
        
        # Generate recommendations (simulating what happens in create route)
        recommendation_data = RecommendationEngine.generate_recommendations(profile, cards)
        
        # Simulate the results route logic
        card_ids = recommendation_data.get('recommended_sequence', [])
        cards_dict = {}
        for card_id in card_ids:
            card = CreditCard.query.get(card_id)
            if card:
                cards_dict[card_id] = card

        # Calculate category totals (this is what we added to the results route)
        category_totals = {}
        card_details = recommendation_data.get('card_details', {})
        for card_id in card_ids:
            details = card_details.get(str(card_id), {})
            category_values = details.get('category_values', {})
            for category, value in category_values.items():
                if value > 0:  # Only include categories with positive value
                    category_totals[category] = category_totals.get(category, 0) + value

        print("🎯 Results Page Simulation:")
        print(f"✅ Profile: {profile.name}")
        print(f"💳 Recommended cards: {len(card_ids)}")
        print(f"📊 Total value: ${recommendation_data['total_value']:.2f}")
        print(f"💰 Total annual fees: ${recommendation_data['total_annual_fees']:.2f}")
        
        print(f"\n🏷️  Category Totals (what will be displayed):")
        if category_totals:
            for category, total_value in category_totals.items():
                print(f"   - {category.capitalize()}: ${total_value:.2f}/month (${total_value*12:.0f}/year)")
        else:
            print("   ⚠️  No category-specific values found")
        
        print(f"\n🃏 Card Details:")
        for card_id in card_ids:
            card = cards_dict.get(card_id)
            details = card_details.get(str(card_id), {})
            if card:
                print(f"   - {card.name}")
                print(f"     Annual Fee: ${details.get('annual_fee', 0):.2f}")
                print(f"     Annual Value: ${details.get('annual_value', 0):.2f}")
                print(f"     Net Value: ${details.get('net_value', 0):.2f}")
                if 'category_values' in details:
                    print(f"     Category Values:")
                    for cat, val in details['category_values'].items():
                        if val > 0:
                            print(f"       - {cat}: ${val:.2f}/month")
        
        # Test template data structure
        print(f"\n🧪 Template Data Structure Test:")
        print(f"   - recommendation: {type(recommendation_data)} with {len(recommendation_data)} keys")
        print(f"   - cards: {type(cards_dict)} with {len(cards_dict)} items")
        print(f"   - category_totals: {type(category_totals)} with {len(category_totals)} items")
        print(f"   - profile: {type(profile)}")
        
        return True

if __name__ == "__main__":
    test_results_page_logic() 
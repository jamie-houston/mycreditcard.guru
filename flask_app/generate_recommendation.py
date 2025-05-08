from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard
from app.blueprints.recommendations.services import RecommendationService
import json

def generate_recommendation():
    app = create_app()
    with app.app_context():
        # Get the profile from the database (using profile ID 2 which has a user_id of 1)
        profile = UserProfile.query.get(2)
        if not profile:
            print("Profile not found")
            return
        
        print(f"Generating recommendation for profile: {profile.name}")
        print(f"Profile ID: {profile.id}")
        print(f"User ID: {profile.user_id}")
        
        try:
            # Generate a recommendation
            recommendation = RecommendationService.generate_recommendation(
                user_id=profile.user_id,
                profile_id=profile.id
            )
            
            print("\nRecommendation generated successfully!")
            print(f"Recommendation ID: {recommendation.id}")
            print(f"Total Value: ${recommendation.total_value}")
            print(f"Total Annual Fees: ${recommendation.total_annual_fees}")
            print(f"Card Count: {recommendation.card_count}")
            print(f"Card IDs: {recommendation.recommended_sequence}")
            
            # Print details about each card
            print("\nRecommended Cards:")
            card_details = recommendation.card_details
            for card_id, details in card_details.items():
                print(f"  Card: {details['card_name']}")
                print(f"  Net Value: ${details['net_value']}")
                print(f"  Annual Fee: ${details['annual_fee']}")
                print(f"  Annual Value: ${details['annual_value']}")
                print(f"  Rewards by Category:")
                for category, value in details['rewards_by_category'].items():
                    print(f"    {category}: ${value}")
                print()
                
        except Exception as e:
            print(f"Error generating recommendation: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generate_recommendation() 
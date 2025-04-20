# Import the Recommendation model from the main models module
from app.models.recommendation import Recommendation

# You can add blueprint-specific methods or extensions here if needed
# For example:

def create_recommendation_from_profile(user_id, profile_id, card_details, sequence, monthly_values=None):
    """Helper function to create a recommendation from a spending profile."""
    total_value = sum(details['annual_value'] for details in card_details.values())
    total_fees = sum(details['annual_fee'] for details in card_details.values())
    
    return Recommendation(
        user_id=user_id,
        profile_id=profile_id,
        card_details=card_details,
        recommended_sequence=sequence,
        per_month_value=monthly_values or [],
        total_value=total_value,
        total_annual_fees=total_fees,
        card_count=len(sequence)
    ) 
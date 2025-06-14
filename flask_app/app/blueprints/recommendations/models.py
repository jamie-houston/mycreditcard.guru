# Import the Recommendation model from the main models module
from app.models.recommendation import Recommendation
from app.models.user_data import UserProfile
import json
import hashlib

# You can add blueprint-specific methods or extensions here if needed
# For example:

def generate_recommendation_id(profile, recommendation_data):
    """Generate a deterministic hash for a recommendation based on profile and recommendation data."""
    # Normalize relevant data
    profile_data = {
        'credit_score': profile.credit_score,
        'income': profile.income,
        'total_monthly_spend': profile.total_monthly_spend,
        'category_spending': profile.get_category_spending(),
        'reward_preferences': profile.get_reward_preferences() if hasattr(profile, 'get_reward_preferences') else [],
        'max_cards': getattr(profile, 'max_cards', 5),
        'max_annual_fees': getattr(profile, 'max_annual_fees', 1000.0),
    }
    # Recommendation data (sort keys for determinism)
    rec_data = {
        'recommended_sequence': recommendation_data.get('recommended_sequence', []),
        'card_details': recommendation_data.get('card_details', {}),
        'total_value': recommendation_data.get('total_value', 0),
        'total_annual_fees': recommendation_data.get('total_annual_fees', 0),
        'per_month_value': recommendation_data.get('per_month_value', []),
    }
    # Serialize and hash
    hash_input = json.dumps({'profile': profile_data, 'recommendation': rec_data}, sort_keys=True)
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def create_recommendation_from_profile(user_id, profile_id, card_details, sequence, monthly_values=None, session_id=None):
    """Helper function to create a recommendation from a spending profile."""
    total_value = sum(details['annual_value'] for details in card_details.values())
    total_fees = sum(details['annual_fee'] for details in card_details.values())
    
    # Get the profile to generate the recommendation ID
    profile = UserProfile.query.get(profile_id)
    if not profile:
        raise ValueError(f"Profile with ID {profile_id} not found")
    
    # Prepare recommendation data for ID generation
    recommendation_data = {
        'recommended_sequence': sequence,
        'card_details': card_details,
        'total_value': total_value,
        'total_annual_fees': total_fees,
        'per_month_value': monthly_values or [],
    }
    
    # Generate deterministic recommendation ID
    recommendation_id = generate_recommendation_id(profile, recommendation_data)
    
    return Recommendation(
        user_id=user_id,
        user_profile_id=profile_id,
        card_details=card_details,
        recommended_sequence=sequence,
        per_month_value=monthly_values or [],
        total_value=total_value,
        total_annual_fees=total_fees,
        card_count=len(sequence),
        recommendation_id=recommendation_id,
        session_id=session_id
    ) 
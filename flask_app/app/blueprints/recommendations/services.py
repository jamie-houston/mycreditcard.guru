from app.models.credit_card import CreditCard
from app.models.user_data import UserProfile
from app.blueprints.recommendations.models import Recommendation, create_recommendation_from_profile
from app import db

class RecommendationService:
    """Service for generating credit card recommendations based on user's spending profile."""
    
    @staticmethod
    def calculate_card_value(card, monthly_spending):
        """
        Calculate the annual value of a credit card based on spending profile.
        
        Args:
            card: CreditCard object
            monthly_spending: Dictionary with spending categories as keys and monthly amounts as values
        
        Returns:
            Dictionary with annual value breakdown
        """
        annual_value = 0
        rewards_by_category = {}
        
        # Calculate rewards for each spending category
        for category, monthly_amount in monthly_spending.items():
            category_reward_rate = 0
            
            # Get the reward rate for this category from the card's reward categories
            categories = card.get_reward_categories()
            for cat_data in categories:
                cat_name = cat_data['category'].lower()
                if cat_name == category.lower() or (category.lower() in ['base rate', 'base'] and cat_name == 'other'):
                    category_reward_rate = float(cat_data.get('rate', cat_data.get('percentage', 0)))
                    break
            
            # Use 'other' if no specific category rate found
            if category_reward_rate == 0:
                for cat_data in categories:
                    if cat_data['category'].lower() == 'other' or cat_data['category'].lower() == 'all':
                        category_reward_rate = float(cat_data.get('rate', cat_data.get('percentage', 0)))
                        break
                if category_reward_rate == 0:
                    category_reward_rate = 1.0  # Default 1% if no base rate found
            
            # Calculate the annual value for this category
            annual_amount = monthly_amount * 12
            # Convert percentage to decimal (e.g., 3.0% becomes 0.03)
            category_value = annual_amount * (category_reward_rate / 100)
            
            rewards_by_category[category] = category_value
            annual_value += category_value
            
        # Add sign-up bonus (already in dollars from the database)
        if card.signup_bonus_value and card.signup_bonus_value > 0:
            signup_bonus_dollars = card.signup_bonus_value
            annual_value += signup_bonus_dollars
            rewards_by_category['signup_bonus'] = signup_bonus_dollars
            
        return {
            'annual_value': annual_value,
            'annual_fee': card.annual_fee,
            'net_value': annual_value - card.annual_fee,
            'rewards_by_category': rewards_by_category
        }
    
    @classmethod
    def generate_recommendation(cls, user_id, profile_id):
        """
        Generate a credit card recommendation based on a user's spending profile.
        
        Args:
            user_id: User ID
            profile_id: Spending profile ID
        
        Returns:
            Recommendation object
        """
        # Get spending profile
        profile = UserProfile.query.get_or_404(profile_id)
        
        # Verify user owns the profile
        if profile.user_id != user_id:
            raise ValueError("User does not own this profile")
        
        # Get spending data from the category_spending JSON
        category_spending = profile.get_category_spending()
        
        # Get all credit cards
        cards = CreditCard.query.all()
        
        # Calculate value for each card
        card_values = {}
        for card in cards:
            card_values[card.id] = cls.calculate_card_value(card, category_spending)
            card_values[card.id]['card_id'] = card.id
            card_values[card.id]['card_name'] = card.name
        
        # Sort cards by net value (value - annual fee)
        sorted_cards = sorted(
            card_values.items(), 
            key=lambda x: x[1]['net_value'], 
            reverse=True
        )
        
        # Get top 5 cards
        top_cards = sorted_cards[:5]
        top_card_ids = [card_id for card_id, _ in top_cards]
        
        # Convert to dictionary for storage
        card_details = {str(card_id): details for card_id, details in dict(top_cards).items()}
        
        # Create monthly value projection
        # This is simplified - in a real app, you might have more complex logic
        monthly_values = []
        for month in range(1, 13):
            # Simplified: just divide annual value by 12
            monthly_value = sum(details['annual_value'] for details in card_details.values()) / 12
            
            # Add signup bonuses only to the first month
            if month == 1:
                signup_value = sum(
                    details['rewards_by_category'].get('signup_bonus', 0)
                    for details in card_details.values()
                )
                monthly_value += signup_value
                
            monthly_values.append(monthly_value)
            
        # Create the recommendation
        recommendation = create_recommendation_from_profile(
            user_id=user_id,
            profile_id=profile_id,
            card_details=card_details,
            sequence=top_card_ids,
            monthly_values=monthly_values
        )
        
        db.session.add(recommendation)
        db.session.commit()
        
        return recommendation
    
    @staticmethod
    def get_user_recommendations(user_id=None, session_id=None):
        """Get all recommendations for a user or session."""
        if user_id:
            return Recommendation.query.filter_by(user_id=user_id).order_by(Recommendation.created_at.desc()).all()
        elif session_id:
            return Recommendation.query.filter_by(session_id=session_id).order_by(Recommendation.created_at.desc()).all()
        return []
    
    @staticmethod
    def get_recommendation(recommendation_id, user_id):
        """Get a specific recommendation for a user."""
        recommendation = Recommendation.query.get_or_404(recommendation_id)
        
        # Verify user owns the recommendation
        if recommendation.user_id != user_id:
            raise ValueError("User does not own this recommendation")
            
        return recommendation
    
    @staticmethod
    def delete_recommendation(recommendation_id, user_id):
        """Delete a recommendation."""
        recommendation = Recommendation.query.get_or_404(recommendation_id)
        
        # Verify user owns the recommendation
        if recommendation.user_id != user_id:
            raise ValueError("User does not own this recommendation")
            
        db.session.delete(recommendation)
        db.session.commit()
        
        return True 
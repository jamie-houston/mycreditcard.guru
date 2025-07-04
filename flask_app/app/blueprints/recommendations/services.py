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
            # Get reward rate and limit from the new rewards relationship
            main_rate = card.get_category_rate(category)
            limit = None
            
            # Get the limit for this specific category if it exists
            from app.models.category import Category
            category_obj = Category.get_by_name_or_alias(category)
            if category_obj:
                reward = card.rewards.filter_by(category_id=category_obj.id).first()
                if reward:
                    limit = reward.limit
            
            # Get base rate (for spend above limit) - always use 'other' category
            base_rate = card.get_category_rate('other')
            annual_amount = monthly_amount * 12
            if limit is not None:
                try:
                    limit = float(limit)
                except Exception:
                    limit = None
            if limit is not None and limit >= 0:
                # Apply main rate up to the limit, base rate for the rest
                main_spend = min(annual_amount, limit)
                base_spend = max(0, annual_amount - limit)
                # Calculate points/miles earned, then convert to dollar value using multiplier
                # Points calculation: spending * (rate as percentage / 100)
                points_earned = main_spend * (main_rate / 100) + base_spend * (base_rate / 100)
                # Dollar value: points * multiplier (where multiplier is already in dollar terms)
                category_value = points_earned * card.reward_value_multiplier
                rewards_by_category[category] = {
                    'main_rate': main_rate,
                    'main_spend': main_spend,
                    'limit': limit,
                    'base_rate': base_rate,
                    'base_spend': base_spend,
                    'points_earned': points_earned,
                    'value': category_value
                }
            else:
                # Calculate points/miles earned, then convert to dollar value using multiplier
                # Points calculation: spending * (rate as percentage / 100)
                points_earned = annual_amount * (main_rate / 100)
                # Dollar value: points * multiplier (where multiplier is already in dollar terms)
                category_value = points_earned * card.reward_value_multiplier
                rewards_by_category[category] = {
                    'main_rate': main_rate,
                    'main_spend': annual_amount,
                    'limit': None,
                    'base_rate': base_rate,
                    'base_spend': 0,
                    'points_earned': points_earned,
                    'value': category_value
                }
            annual_value += category_value
            
        # Add sign-up bonus (calculated value from JSON structure)
        signup_bonus_value = card.get_signup_bonus_value_new()
        if signup_bonus_value > 0:
            annual_value += signup_bonus_value
            rewards_by_category['signup_bonus'] = signup_bonus_value
            
        return {
            'annual_value': annual_value,
            'annual_fee': card.annual_fee,
            'net_value': annual_value - card.annual_fee,
            'rewards_by_category': rewards_by_category
        }
    
    @classmethod
    def generate_recommendation(cls, user_id=None, profile_id=None, session_id=None):
        """
        Generate a credit card recommendation based on a user's spending profile.
        
        Args:
            user_id: User ID (for authenticated users)
            profile_id: Spending profile ID
            session_id: Session ID (for anonymous users)
        
        Returns:
            Recommendation object
        """
        # Get spending profile
        profile = UserProfile.query.get_or_404(profile_id)
        
        # Verify user/session owns the profile
        if not ((user_id and profile.user_id == user_id) or 
                (session_id and profile.session_id == session_id)):
            raise ValueError("User/session does not own this profile")
        
        # Get spending data from the category_spending JSON
        category_spending = profile.get_category_spending()
        
        # Get credit cards, filtered by preferred issuer if specified
        if profile.preferred_issuer_id:
            cards = CreditCard.query.filter_by(issuer_id=profile.preferred_issuer_id).all()
        else:
            cards = CreditCard.query.all()
        
        # Filter cards by reward type preference
        reward_type = profile.get_reward_type()
        cards = [card for card in cards if card.reward_type == reward_type]
        
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
        
        # Select top cards based on constraints
        max_cards = profile.max_cards or 1
        max_fee_limit = profile.max_annual_fees  # May be None
        selected_cards = []
        total_fees = 0.0
        for card_id, details in sorted_cards:
            fee = details['annual_fee']
            if max_fee_limit is not None and fee + total_fees > max_fee_limit:
                continue  # Skip cards that would exceed fee limit
            selected_cards.append((card_id, details))
            total_fees += fee
            if len(selected_cards) >= max_cards:
                break
        
        # Only fall back to first card if no fee limit was set
        # If user set a fee limit and no cards meet it, return empty recommendation
        if not selected_cards and sorted_cards and max_fee_limit is None:
            selected_cards.append(sorted_cards[0])
        
        # If no cards were selected due to fee constraints, raise an error
        if not selected_cards:
            if max_fee_limit is not None:
                raise ValueError(f"No cards found within your maximum annual fee limit of ${max_fee_limit}. Consider increasing your fee limit or adjusting your preferences.")
            else:
                raise ValueError("No cards found matching your criteria.")
        
        top_cards = selected_cards
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
        
        # Create the recommendation (this generates the deterministic ID)
        recommendation = create_recommendation_from_profile(
            user_id=user_id,
            profile_id=profile_id,
            card_details=card_details,
            sequence=top_card_ids,
            monthly_values=monthly_values,
            session_id=session_id
        )
        
        # Check if a recommendation with this ID already exists
        existing_recommendation = Recommendation.query.filter_by(
            recommendation_id=recommendation.recommendation_id
        ).first()
        
        if existing_recommendation:
            # Return the existing recommendation instead of creating a duplicate
            return existing_recommendation
        
        # If no existing recommendation, save the new one
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
    def get_recommendation(recommendation_id, user_id=None, session_id=None):
        """Get a specific recommendation for a user or session."""
        recommendation = Recommendation.query.get_or_404(recommendation_id)
        if (user_id and recommendation.user_id == user_id) or (session_id and recommendation.session_id == session_id):
            return recommendation
        raise ValueError("User does not own this recommendation")
    
    @staticmethod
    def delete_recommendation(recommendation_id, user_id=None, session_id=None):
        """Delete a recommendation for a user or session."""
        recommendation = Recommendation.query.get_or_404(recommendation_id)
        if (user_id and recommendation.user_id == user_id) or (session_id and recommendation.session_id == session_id):
            db.session.delete(recommendation)
            db.session.commit()
            return True
        raise ValueError("User does not own this recommendation") 
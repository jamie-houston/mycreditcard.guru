from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user
from app import db
from app.blueprints.recommendations import bp
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from datetime import datetime
from app.blueprints.recommendations.services import RecommendationService
from app.models.user_data import UserProfile

@bp.route('/')
def list():
    """List all recommendations for the current user."""
    user_recommendations = RecommendationService.get_user_recommendations(current_user.id)
    
    # Get all profiles for the current user
    profiles = {}
    for profile in UserProfile.query.filter_by(user_id=current_user.id).all():
        profiles[profile.id] = profile
    
    return render_template(
        'recommendations/list.html',
        recommendations=user_recommendations,
        profiles=profiles
    )

@bp.route('/create/<int:profile_id>')
def create(profile_id):
    """Create a new recommendation based on a spending profile."""
    try:
        # Verify profile exists
        profile = UserProfile.query.get_or_404(profile_id)
        
        # Check permissions - profile must belong to current user or session
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('anonymous_user_id')
        
        if not ((user_id and profile.user_id == user_id) or 
                (session_id and profile.session_id == session_id)):
            flash('You do not have permission to access this profile.', 'danger')
            if current_user.is_authenticated:
                return redirect(url_for('recommendations.list'))
            else:
                return redirect(url_for('user_data.profile'))
        
        # Generate recommendation
        recommendation = RecommendationService.generate_recommendation(
            user_id=user_id, 
            profile_id=profile_id,
            session_id=session_id
        )
        
        flash('Recommendation generated successfully!', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.recommendation_id))
    
    except Exception as e:
        flash(f'Error generating recommendation: {str(e)}', 'danger')
        if current_user.is_authenticated:
            return redirect(url_for('recommendations.list'))
        else:
            return redirect(url_for('user_data.profile'))

@bp.route('/view/<recommendation_id>')
def view(recommendation_id):
    """View a specific recommendation by its shareable ID."""
    try:
        # Get recommendation by recommendation_id (not database ID)
        recommendation = Recommendation.query.filter_by(recommendation_id=recommendation_id).first()
        if not recommendation:
            flash('Recommendation not found.', 'warning')
            return redirect(url_for('user_data.profile'))
        
        # Check if user has permission (for authenticated users) or if it's anonymous
        if current_user.is_authenticated:
            if recommendation.user_id and recommendation.user_id != current_user.id:
                flash('You do not have permission to view this recommendation.', 'danger')
                return redirect(url_for('recommendations.list'))
        else:
            # For anonymous users, check session_id if it exists
            session_id = session.get('anonymous_user_id')
            if recommendation.session_id and session_id and recommendation.session_id != session_id:
                # Allow viewing even if session doesn't match - recommendations are shareable
                pass
        
        # Get cards in the recommendation
        card_ids = recommendation.recommended_sequence
        cards = {card.id: card for card in CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()}
        
        # Get the profile for additional context
        profile = UserProfile.query.get(recommendation.user_profile_id)
        
        # Calculate which categories each card is optimal for (category exclusivity)
        card_details = recommendation.card_details
        optimal_categories = {}  # card_id -> set of categories where this card is optimal
        
        # Find all categories across all cards
        all_categories = set()
        for card_id in card_ids:
            details = card_details.get(str(card_id), {})
            rewards_by_category = details.get('rewards_by_category', {})
            all_categories.update(rewards_by_category.keys())
        
        # For each category, find which card has the highest value
        for category in all_categories:
            if category == 'signup_bonus':
                continue  # Skip signup bonus in category optimization
            
            best_card_id = None
            max_value = 0
            
            for card_id in card_ids:
                details = card_details.get(str(card_id), {})
                rewards_by_category = details.get('rewards_by_category', {})
                reward_info = rewards_by_category.get(category, {})
                
                if isinstance(reward_info, dict) and 'value' in reward_info:
                    value = reward_info['value']
                    if value > max_value:
                        max_value = value
                        best_card_id = card_id
            
            # Assign this category to the best card
            if best_card_id and max_value > 0:
                if best_card_id not in optimal_categories:
                    optimal_categories[best_card_id] = set()
                optimal_categories[best_card_id].add(category)
        
        return render_template(
            'recommendations/view.html',
            recommendation=recommendation,
            cards=cards,
            profile=profile,
            optimal_categories=optimal_categories
        )
    
    except Exception as e:
        flash(f'Error viewing recommendation: {str(e)}', 'danger')
        return redirect(url_for('user_data.profile'))

@bp.route('/delete/<recommendation_id>', methods=['POST'])
def delete(recommendation_id):
    """Delete a recommendation by its shareable ID."""
    try:
        # Get recommendation by recommendation_id
        recommendation = Recommendation.query.filter_by(recommendation_id=recommendation_id).first()
        if not recommendation:
            flash('Recommendation not found.', 'warning')
            return redirect(url_for('recommendations.list'))
        
        # Check permissions
        user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
        session_id = session.get('anonymous_user_id')
        
        if not ((user_id and recommendation.user_id == user_id) or 
                (session_id and recommendation.session_id == session_id)):
            flash('You do not have permission to delete this recommendation.', 'danger')
            return redirect(url_for('recommendations.list'))
        
        # Delete the recommendation
        db.session.delete(recommendation)
        db.session.commit()
        
        flash('Recommendation deleted successfully!', 'success')
    
    except Exception as e:
        flash(f'Error deleting recommendation: {str(e)}', 'danger')
    
    return redirect(url_for('recommendations.list'))

@bp.route('/remove_card/<recommendation_id>/<int:card_id>', methods=['POST'])
def remove_card(recommendation_id, card_id):
    """Remove a card from a recommendation and create a new recommendation."""
    try:
        # Get the original recommendation
        recommendation = Recommendation.query.filter_by(recommendation_id=recommendation_id).first()
        if not recommendation:
            flash('Recommendation not found.', 'warning')
            return redirect(url_for('user_data.profile'))
        
        # Check permissions
        user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
        session_id = session.get('anonymous_user_id')
        
        if not ((user_id and recommendation.user_id == user_id) or 
                (session_id and recommendation.session_id == session_id)):
            flash('You do not have permission to modify this recommendation.', 'danger')
            return redirect(url_for('recommendations.view', recommendation_id=recommendation_id))
        
        # Remove the card from the recommendation
        new_sequence = [cid for cid in recommendation.recommended_sequence if cid != card_id]
        
        if len(new_sequence) == 0:
            flash('Cannot remove all cards from recommendation.', 'warning')
            return redirect(url_for('recommendations.view', recommendation_id=recommendation_id))
        
        # Create new card details without the removed card
        new_card_details = {str(cid): details for cid, details in recommendation.card_details.items() if int(cid) != card_id}
        
        # Recalculate totals
        new_total_value = sum(details.get('annual_value', 0) for details in new_card_details.values())
        new_total_annual_fees = sum(details.get('annual_fee', 0) for details in new_card_details.values())
        
        # Create a new recommendation
        new_recommendation = Recommendation()
        new_recommendation.user_profile_id = recommendation.user_profile_id
        new_recommendation.user_id = recommendation.user_id
        new_recommendation.session_id = recommendation.session_id
        new_recommendation.spending_profile = recommendation.spending_profile
        new_recommendation.card_preferences = recommendation.card_preferences
        new_recommendation.recommended_sequence = new_sequence
        new_recommendation.card_details = new_card_details
        new_recommendation.total_value = new_total_value
        new_recommendation.total_annual_fees = new_total_annual_fees
        new_recommendation.per_month_value = recommendation.per_month_value  # Keep original for now
        new_recommendation.card_count = len(new_sequence)
        
        # Generate new recommendation ID
        import hashlib
        import json
        hash_input = json.dumps({
            'sequence': new_sequence,
            'details': new_card_details,
            'profile_id': recommendation.user_profile_id
        }, sort_keys=True)
        new_recommendation.recommendation_id = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        # Save the new recommendation
        db.session.add(new_recommendation)
        db.session.commit()
        
        # Get the removed card name for the flash message
        removed_card = CreditCard.query.get(card_id)
        card_name = removed_card.name if removed_card else f"Card {card_id}"
        
        flash(f'Removed {card_name} from recommendation. New recommendation created.', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=new_recommendation.recommendation_id))
    
    except Exception as e:
        flash(f'Error removing card: {str(e)}', 'danger')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation_id)) 
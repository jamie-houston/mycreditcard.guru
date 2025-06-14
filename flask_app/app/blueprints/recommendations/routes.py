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
        # Verify profile exists and belongs to user
        profile = UserProfile.query.get_or_404(profile_id)
        if profile.user_id != current_user.id:
            flash('You do not have permission to access this profile.', 'danger')
            return redirect(url_for('recommendations.list'))
        
        # Generate recommendation
        recommendation = RecommendationService.generate_recommendation(
            user_id=current_user.id, 
            profile_id=profile_id
        )
        
        flash('Recommendation generated successfully!', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.recommendation_id))
    
    except Exception as e:
        flash(f'Error generating recommendation: {str(e)}', 'danger')
        return redirect(url_for('recommendations.list'))

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
        
        return render_template(
            'recommendations/view.html',
            recommendation=recommendation,
            cards=cards,
            profile=profile
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
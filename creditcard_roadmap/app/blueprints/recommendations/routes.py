from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.blueprints.recommendations import bp
from app.models.recommendation import Recommendation
from app.models.user_profile import UserProfile
from app.models.credit_card import CreditCard
from datetime import datetime
from app.blueprints.recommendations.services import RecommendationService
from app.models.user_data import UserProfile as SpendingProfile

@bp.route('/')
@login_required
def list():
    """List all recommendations for the current user."""
    user_recommendations = RecommendationService.get_user_recommendations(current_user.id)
    profiles = {profile.id: profile for profile in current_user.spending_profiles}
    
    return render_template(
        'recommendations/list.html',
        recommendations=user_recommendations,
        profiles=profiles
    )

@bp.route('/create/<int:profile_id>')
@login_required
def create(profile_id):
    """Create a new recommendation based on a spending profile."""
    try:
        # Verify profile exists and belongs to user
        profile = SpendingProfile.query.get_or_404(profile_id)
        if profile.user_id != current_user.id:
            flash('You do not have permission to access this profile.', 'danger')
            return redirect(url_for('recommendations.list'))
        
        # Generate recommendation
        recommendation = RecommendationService.generate_recommendation(
            user_id=current_user.id, 
            profile_id=profile_id
        )
        
        flash('Recommendation generated successfully!', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.id))
    
    except Exception as e:
        flash(f'Error generating recommendation: {str(e)}', 'danger')
        return redirect(url_for('recommendations.list'))

@bp.route('/view/<int:recommendation_id>')
@login_required
def view(recommendation_id):
    """View a specific recommendation."""
    try:
        # Get recommendation
        recommendation = RecommendationService.get_recommendation(
            recommendation_id=recommendation_id,
            user_id=current_user.id
        )
        
        # Get cards in the recommendation
        card_ids = recommendation.recommended_sequence
        cards = {card.id: card for card in CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()}
        
        return render_template(
            'recommendations/view.html',
            recommendation=recommendation,
            cards=cards
        )
    
    except ValueError:
        flash('You do not have permission to view this recommendation.', 'danger')
        return redirect(url_for('recommendations.list'))
    
    except Exception as e:
        flash(f'Error viewing recommendation: {str(e)}', 'danger')
        return redirect(url_for('recommendations.list'))

@bp.route('/delete/<int:recommendation_id>')
@login_required
def delete(recommendation_id):
    """Delete a recommendation."""
    try:
        # Delete recommendation
        RecommendationService.delete_recommendation(
            recommendation_id=recommendation_id,
            user_id=current_user.id
        )
        
        flash('Recommendation deleted successfully!', 'success')
    
    except ValueError:
        flash('You do not have permission to delete this recommendation.', 'danger')
    
    except Exception as e:
        flash(f'Error deleting recommendation: {str(e)}', 'danger')
    
    return redirect(url_for('recommendations.list')) 
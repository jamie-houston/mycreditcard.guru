from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from datetime import datetime
from app import db
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from app.models.user_profile import UserProfile
from app.services.recommendation_engine import generate_recommendations

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

@bp.route('/')
def list():
    """List all recommendations for the current user."""
    recommendations = Recommendation.query.filter_by(user_id=current_user.id).order_by(Recommendation.created_at.desc()).all()
    return render_template('recommendations/list.html', recommendations=recommendations)

@bp.route('/<int:recommendation_id>')
def view(recommendation_id):
    """View a specific recommendation."""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    # Get all card details
    card_ids = recommendation.recommended_sequence
    card_objects = CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()
    cards = {card.id: card for card in card_objects}
    
    return render_template('recommendations/view.html', recommendation=recommendation, cards=cards)

@bp.route('/generate/<int:profile_id>')
def generate(profile_id):
    """Generate a new recommendation based on a user profile."""
    profile = UserProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    
    try:
        # Generate recommendations using the service
        recommendation_data = generate_recommendations(profile)
        
        # Create new recommendation record
        recommendation = Recommendation(
            user_id=current_user.id,
            profile_id=profile.id,
            recommended_sequence=recommendation_data['recommended_sequence'],
            card_details=recommendation_data['card_details'],
            total_value=recommendation_data['total_value'],
            total_annual_fees=recommendation_data['total_annual_fees'],
            card_count=len(recommendation_data['recommended_sequence']),
            per_month_value=recommendation_data['per_month_value']
        )
        
        db.session.add(recommendation)
        db.session.commit()
        
        flash('Recommendation generated successfully!', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.id))
    
    except Exception as e:
        current_app.logger.error(f"Error generating recommendation: {str(e)}")
        flash('Error generating recommendation. Please try again.', 'danger')
        return redirect(url_for('profiles.view', profile_id=profile_id))

@bp.route('/delete/<int:recommendation_id>', methods=['GET'])
def delete(recommendation_id):
    """Delete a recommendation."""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(recommendation)
        db.session.commit()
        flash('Recommendation deleted successfully!', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting recommendation: {str(e)}")
        flash('Error deleting recommendation.', 'danger')
        
    return redirect(url_for('recommendations.list')) 
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from datetime import datetime
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from app.models.user_profile import UserProfile
from app.services import recommendation_service
from app import db

recommendations_bp = Blueprint('recommendations', __name__)

@recommendations_bp.route('/list')
def list():
    """Display a list of the user's saved recommendations."""
    recommendations = Recommendation.query.filter_by(user_id=current_user.id).order_by(Recommendation.created_at.desc()).all()
    return render_template('recommendations/list.html', recommendations=recommendations)

@recommendations_bp.route('/create/<int:profile_id>', methods=['GET', 'POST'])
def create(profile_id):
    """Create a new credit card recommendation based on a user profile."""
    # Get the user profile
    profile = UserProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    
    # Get all available credit cards
    all_cards = CreditCard.query.all()
    cards_dict = {str(card.id): card.to_dict() for card in all_cards}
    
    # Create a new recommendation
    recommendation = recommendation_service.generate_recommendation(
        profile=profile,
        user=current_user,
        available_cards=cards_dict
    )
    
    db.session.add(recommendation)
    db.session.commit()
    
    flash('Your credit card recommendation has been created!', 'success')
    return redirect(url_for('recommendations.view', recommendation_id=recommendation.id))

@recommendations_bp.route('/view/<int:recommendation_id>')
def view(recommendation_id):
    """View a specific recommendation."""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    # Get all cards referenced in this recommendation
    card_ids = recommendation.recommended_sequence
    cards = {card.id: card for card in CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()}
    
    return render_template('recommendations/view.html', recommendation=recommendation, cards=cards)

@recommendations_bp.route('/delete/<int:recommendation_id>')
def delete(recommendation_id):
    """Delete a recommendation."""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(recommendation)
    db.session.commit()
    
    flash('Recommendation deleted successfully.', 'success')
    return redirect(url_for('recommendations.list')) 
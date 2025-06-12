from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from creditcard_roadmap.app.models import Profile, CreditCard, Recommendation
from creditcard_roadmap.app.recommendations.engine import generate_recommendations
from creditcard_roadmap.app import db
from flask_login import login_required, current_user
from sqlalchemy import asc
from typing import Dict
import json
from datetime import datetime

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

@recommendations_bp.route('/generate', methods=['POST'])
def generate():
    """Generate credit card recommendations based on user profile"""
    try:
        profile_id = request.form.get('profile_id')
        if not profile_id:
            flash('No profile selected', 'danger')
            return redirect(url_for('user_data.profiles'))
        
        profile = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first()
        if not profile:
            flash('Profile not found', 'danger')
            return redirect(url_for('user_data.profiles'))
        
        # Call recommendation engine
        recommendation_data = generate_recommendations(profile)
        
        # Create new recommendation record
        recommendation = Recommendation(
            user_id=current_user.id,
            profile_id=profile.id,
            total_value=recommendation_data['total_value'],
            total_annual_fees=recommendation_data['total_annual_fees'],
            card_count=len(recommendation_data['recommended_sequence']),
            recommended_sequence=recommendation_data['recommended_sequence'],
            card_details=recommendation_data['card_details'],
            per_month_value=recommendation_data['per_month_value']
        )
        
        db.session.add(recommendation)
        db.session.commit()
        
        flash('Recommendation generated successfully', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.id))
        
    except Exception as e:
        current_app.logger.error(f"Error generating recommendation: {str(e)}")
        flash('An error occurred while generating recommendations', 'danger')
        return redirect(url_for('user_data.profiles'))

@recommendations_bp.route('/view/<int:recommendation_id>')
def view(recommendation_id):
    """View a saved recommendation"""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    # Get all the credit cards referenced in the recommendation
    card_ids = recommendation.recommended_sequence
    cards = {card.id: card for card in CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()}
    
    return render_template('recommendations/view.html', recommendation=recommendation, cards=cards)

@recommendations_bp.route('/list')
def list():
    """List all saved recommendations"""
    recommendations = Recommendation.query.filter_by(user_id=current_user.id).order_by(Recommendation.created_at.desc()).all()
    return render_template('recommendations/list.html', recommendations=recommendations)

@recommendations_bp.route('/delete/<int:recommendation_id>')
def delete(recommendation_id):
    """Delete a saved recommendation"""
    recommendation = Recommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(recommendation)
    db.session.commit()
    
    flash('Recommendation deleted successfully', 'success')
    return redirect(url_for('recommendations.list')) 
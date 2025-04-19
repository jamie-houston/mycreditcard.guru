from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.user_data import UserProfile, Recommendation
from app.models.credit_card import CreditCard
from app.utils.recommendation_engine import generate_card_recommendations
from datetime import datetime
import json

recommendations = Blueprint('recommendations', __name__)

@recommendations.route('/generate')
def generate():
    """Generate credit card recommendations based on user profile."""
    # Check if user has a profile
    profile_id = session.get('profile_id')
    if not profile_id:
        flash('Please complete your profile first', 'warning')
        return redirect(url_for('user_data.profile'))
    
    profile = UserProfile.query.get_or_404(profile_id)
    
    # Get all active credit cards
    cards = CreditCard.query.filter_by(is_active=True).all()
    
    if not cards:
        flash('No credit cards available in the system', 'warning')
        return render_template('recommendations/empty.html')
    
    # Generate recommendations
    recommendation_data, total_value = generate_card_recommendations(
        profile, 
        cards, 
        max_cards=profile.max_cards, 
        max_annual_fees=profile.max_annual_fees
    )
    
    # Save recommendation to database
    recommendation = Recommendation(
        user_profile_id=profile.id,
        recommendation_data=json.dumps(recommendation_data),
        total_estimated_value=total_value
    )
    db.session.add(recommendation)
    db.session.commit()
    
    # Store recommendation ID in session
    session['recommendation_id'] = recommendation.id
    
    return redirect(url_for('recommendations.show', id=recommendation.id))

@recommendations.route('/<int:id>')
def show(id):
    """Display a specific recommendation."""
    recommendation = Recommendation.query.get_or_404(id)
    
    # Parse JSON recommendation data
    try:
        recommendation_data = json.loads(recommendation.recommendation_data)
    except (json.JSONDecodeError, TypeError):
        recommendation_data = []
    
    # Get the full card details for each recommended card
    card_details = []
    for item in recommendation_data:
        card = CreditCard.query.get(item['card_id'])
        if card:
            card_details.append({
                'card': card,
                'signup_month': item['signup_month'],
                'cancel_month': item.get('cancel_month'),
                'estimated_value': item['estimated_value']
            })
    
    # Parse user profile data for display
    try:
        category_spending = json.loads(recommendation.user_profile.category_spending)
        reward_preferences = json.loads(recommendation.user_profile.reward_preferences)
    except (json.JSONDecodeError, TypeError):
        category_spending = {}
        reward_preferences = []
    
    return render_template('recommendations/show.html', 
                          recommendation=recommendation,
                          card_details=card_details,
                          profile=recommendation.user_profile,
                          category_spending=category_spending,
                          reward_preferences=reward_preferences) 
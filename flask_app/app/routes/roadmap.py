"""Routes for credit card roadmap and portfolio management."""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import current_user
from datetime import datetime, date
import json

from app import db
from app.models.credit_card import CreditCard
from app.models.user_card import UserCard
from app.models.user_data import UserProfile
from app.models.issuer_policy import IssuerPolicy
from app.engine.roadmap_engine import RoadmapEngine

roadmap = Blueprint('roadmap', __name__)

def get_user_identifier():
    """Get user ID or session ID for current user."""
    if current_user.is_authenticated:
        return {'user_id': current_user.id}
    else:
        return {'session_id': session.get('anonymous_user_id')}

@roadmap.route('/portfolio')
def portfolio():
    """Display user's current credit card portfolio."""
    user_ident = get_user_identifier()
    user_cards = UserCard.get_user_cards(**user_ident)
    
    # Get user profile for spending data
    user_profile = None
    if current_user.is_authenticated:
        user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    else:
        # For anonymous users, try to get profile from session
        profile_data = session.get('user_profile')
        if profile_data:
            user_profile = UserProfile()
            for key, value in profile_data.items():
                if hasattr(user_profile, key):
                    setattr(user_profile, key, value)
    
    if not user_profile:
        flash('Please set up your spending profile first to see portfolio recommendations.', 'info')
        return redirect(url_for('user_data.profile'))
    
    # Generate current roadmap
    roadmap_engine = RoadmapEngine(user_profile, user_cards)
    current_roadmap = roadmap_engine.generate_current_roadmap()
    
    return render_template('roadmap/portfolio.html', 
                         user_cards=user_cards,
                         current_roadmap=current_roadmap,
                         user_profile=user_profile)

@roadmap.route('/recommendations')
def recommendations():
    """Display roadmap recommendations for new cards, cancellations, etc."""
    user_ident = get_user_identifier()
    user_cards = UserCard.get_user_cards(**user_ident)
    
    # Get user profile
    user_profile = None
    if current_user.is_authenticated:
        user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    else:
        profile_data = session.get('user_profile')
        if profile_data:
            user_profile = UserProfile()
            for key, value in profile_data.items():
                if hasattr(user_profile, key):
                    setattr(user_profile, key, value)
    
    if not user_profile:
        flash('Please set up your spending profile first to get recommendations.', 'info')
        return redirect(url_for('user_data.profile'))
    
    # Generate recommendations
    roadmap_engine = RoadmapEngine(user_profile, user_cards)
    recommendations = roadmap_engine.generate_optimization_recommendations()
    timeline = roadmap_engine.generate_application_timeline()
    
    return render_template('roadmap/recommendations.html',
                         recommendations=recommendations,
                         timeline=timeline,
                         user_profile=user_profile)

@roadmap.route('/add_card', methods=['GET', 'POST'])
def add_card():
    """Add a card to user's portfolio."""
    if request.method == 'GET':
        # Show form to add card
        available_cards = CreditCard.query.filter_by(is_active=True).all()
        user_ident = get_user_identifier()
        owned_card_ids = {uc.credit_card_id for uc in UserCard.get_user_cards(**user_ident)}
        
        # Filter out already owned cards
        available_cards = [card for card in available_cards if card.id not in owned_card_ids]
        
        return render_template('roadmap/add_card.html', available_cards=available_cards)
    
    # Handle POST - add the card
    try:
        card_id = int(request.form.get('card_id'))
        date_acquired = datetime.strptime(request.form.get('date_acquired'), '%Y-%m-%d').date()
        
        # Custom bonus fields (optional)
        custom_bonus_points = request.form.get('custom_bonus_points')
        custom_bonus_value = request.form.get('custom_bonus_value') 
        custom_min_spend = request.form.get('custom_min_spend')
        bonus_earned = request.form.get('bonus_earned') == 'on'
        
        user_ident = get_user_identifier()
        
        # Create new UserCard
        user_card = UserCard(
            credit_card_id=card_id,
            date_acquired=date_acquired,
            bonus_earned=bonus_earned,
            **user_ident
        )
        
        # Set custom bonus values if provided
        if custom_bonus_points:
            user_card.custom_signup_bonus_points = int(custom_bonus_points)
        if custom_bonus_value:
            user_card.custom_signup_bonus_value = float(custom_bonus_value)
        if custom_min_spend:
            user_card.custom_signup_bonus_min_spend = float(custom_min_spend)
        
        db.session.add(user_card)
        db.session.commit()
        
        card = CreditCard.query.get(card_id)
        flash(f'Successfully added {card.name} to your portfolio!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding card: {str(e)}', 'error')
    
    return redirect(url_for('roadmap.portfolio'))

@roadmap.route('/update_card/<int:user_card_id>', methods=['POST'])
def update_card(user_card_id):
    """Update a card in user's portfolio."""
    user_ident = get_user_identifier()
    
    # Find the user card
    query = UserCard.query.filter_by(id=user_card_id)
    if 'user_id' in user_ident:
        query = query.filter_by(user_id=user_ident['user_id'])
    else:
        query = query.filter_by(session_id=user_ident['session_id'])
    
    user_card = query.first()
    if not user_card:
        return jsonify({'error': 'Card not found'}), 404
    
    try:
        # Update fields
        if 'bonus_earned' in request.form:
            user_card.bonus_earned = request.form.get('bonus_earned') == 'on'
            if user_card.bonus_earned and not user_card.bonus_earned_date:
                user_card.bonus_earned_date = date.today()
        
        if 'is_active' in request.form:
            user_card.is_active = request.form.get('is_active') == 'on'
            if not user_card.is_active and not user_card.date_cancelled:
                user_card.date_cancelled = date.today()
        
        db.session.commit()
        flash('Card updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating card: {str(e)}', 'error')
    
    return redirect(url_for('roadmap.portfolio'))

@roadmap.route('/api/card_value/<int:card_id>')
def api_card_value(card_id):
    """API endpoint to calculate card value for current user."""
    user_ident = get_user_identifier()
    
    # Get user profile
    user_profile = None
    if 'user_id' in user_ident:
        user_profile = UserProfile.query.filter_by(user_id=user_ident['user_id']).first()
    else:
        profile_data = session.get('user_profile')
        if profile_data:
            user_profile = UserProfile()
            for key, value in profile_data.items():
                if hasattr(user_profile, key):
                    setattr(user_profile, key, value)
    
    if not user_profile:
        return jsonify({'error': 'No user profile found'}), 400
    
    card = CreditCard.query.get(card_id)
    if not card:
        return jsonify({'error': 'Card not found'}), 404
    
    # Calculate card value
    user_cards = UserCard.get_user_cards(**user_ident)
    roadmap_engine = RoadmapEngine(user_profile, user_cards)
    annual_value = roadmap_engine._calculate_annual_card_value(card)
    
    return jsonify({
        'card_id': card_id,
        'card_name': card.name,
        'annual_value': round(annual_value, 2),
        'annual_fee': card.annual_fee,
        'net_value': round(annual_value - card.annual_fee, 2)
    })
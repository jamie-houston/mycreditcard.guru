from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app import db
from app.models.user_data import UserProfile, Recommendation
from app.models.credit_card import CreditCard
from app.engine.recommendation import generate_recommendations
from datetime import datetime
import json

recommendations = Blueprint('recommendations', __name__)

# Register template filter right after blueprint creation
@recommendations.app_template_filter('from_json')
def from_json_filter(json_string):
    """Convert a JSON string to Python object in templates"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return []

@recommendations.route('/')
def show():
    """Display credit card recommendations based on user profile."""
    # Get the user profile
    profile = UserProfile.query.first()
    
    if not profile:
        flash('Please create your spending profile first.', 'warning')
        return redirect(url_for('user_data.profile'))
    
    # Get the available credit cards
    cards = CreditCard.query.filter_by(is_active=True).all()
    
    if not cards:
        flash('No credit cards available in the database.', 'warning')
        return redirect(url_for('credit_cards.index'))
    
    # Generate recommendations based on user profile and available cards
    try:
        recommendation = generate_recommendations(profile, cards)
        
        # Get category spending as a dictionary
        category_spending = profile.get_category_spending()
        
        # Prepare card details for display
        card_details = []
        for card_id, details in recommendation.get('card_details', {}).items():
            card = next((c for c in cards if c.id == int(card_id)), None)
            if card:
                card_details.append({
                    'card': card,
                    'estimated_value': details.get('estimated_value', 0),
                    'signup_month': details.get('signup_month', 'Anytime')
                })
        
        # Sort card details by estimated value (highest first)
        card_details.sort(key=lambda x: x['estimated_value'], reverse=True)
        
        return render_template(
            'recommendations/show.html',
            profile=profile,
            category_spending=category_spending,
            recommendation=recommendation,
            card_details=card_details
        )
    except Exception as e:
        flash(f'Error generating recommendations: {str(e)}', 'danger')
        current_app.logger.error(f'Recommendation error: {str(e)}')
        return redirect(url_for('main.index'))

@recommendations.route('/create/<int:profile_id>', methods=['GET', 'POST'])
def create(profile_id):
    """Generate credit card recommendations for a user profile."""
    # Get the user profile
    profile = UserProfile.query.get_or_404(profile_id)
    
    if request.method == 'POST':
        try:
            # Get all credit cards from the database
            cards = CreditCard.query.all()
            
            # Generate recommendations
            recommendation_data = generate_recommendations(profile, cards)
            
            # Store recommendation data in session to retrieve later
            session['recommendation_data'] = recommendation_data
            
            # Redirect to results page
            return redirect(url_for('recommendations.results', profile_id=profile.id))
            
        except Exception as e:
            flash(f'Error generating recommendations: {str(e)}', 'danger')
            return redirect(url_for('recommendations.create', profile_id=profile.id))
    
    # GET request - show the recommendation form
    return render_template('recommendations/generate.html', profile=profile)

@recommendations.route('/results/<int:profile_id>')
def results(profile_id: int):
    """Show recommendation results for a user profile."""
    # Get the user profile
    profile = UserProfile.query.get_or_404(profile_id)
    
    # Get recommendation data from session
    recommendation_data = session.get('recommendation_data')
    
    if not recommendation_data:
        flash('No recommendation data found. Please generate recommendations first.', 'warning')
        return redirect(url_for('recommendations.create', profile_id=profile.id))
    
    # Get cards for the recommendation
    card_ids = recommendation_data.get('cards', [])
    cards = CreditCard.query.filter(CreditCard.id.in_(card_ids)).all()
    
    # Render the results template
    return render_template(
        'recommendations/results.html',
        profile=profile,
        recommendation=recommendation_data,
        cards=cards
    )

@recommendations.route('/compare/<int:profile_id>')
def compare(profile_id: int):
    """Compare multiple recommendation strategies."""
    # Get the user profile
    profile = UserProfile.query.get_or_404(profile_id)
    
    # Get recommendation data from session
    recommendation_data = session.get('recommendation_data')
    
    if not recommendation_data:
        flash('No recommendation data found. Please generate recommendations first.', 'warning')
        return redirect(url_for('recommendations.create', profile_id=profile.id))
    
    # Get all cards from the database
    cards = CreditCard.query.all()
    
    # Generate alternative recommendation strategies
    # For example, one focused on cashback, one on travel, etc.
    strategies = {
        'balanced': recommendation_data,
        'cashback_focused': generate_recommendations(profile, [c for c in cards if c.reward_type == 'cashback']),
        'travel_focused': generate_recommendations(profile, [c for c in cards if c.reward_type == 'travel']),
        'no_annual_fee': generate_recommendations(profile, [c for c in cards if c.annual_fee == 0])
    }
    
    # Render the comparison template
    return render_template(
        'recommendations/compare.html',
        profile=profile,
        strategies=strategies,
        cards=cards
    )

@recommendations.route('/download/<int:profile_id>')
def download(profile_id: int):
    """Download recommendation data as JSON."""
    # Get recommendation data from session
    recommendation_data = session.get('recommendation_data')
    
    if not recommendation_data:
        flash('No recommendation data found. Please generate recommendations first.', 'warning')
        return redirect(url_for('recommendations.create', profile_id=profile.id))
    
    # Convert to JSON
    recommendation_json = json.dumps(recommendation_data, indent=2)
    
    # Create response
    from flask import Response
    response = Response(
        recommendation_json,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment;filename=card_recommendations_{profile_id}.json'
        }
    )
    
    return response

@recommendations.route('/show/<int:recommendation_id>')
def show(recommendation_id):
    """Show recommendation details."""
    recommendation = Recommendation.query.get_or_404(recommendation_id)
    profile = UserProfile.query.get_or_404(recommendation.user_profile_id)
    
    # Parse recommendation data
    recommendation_data = json.loads(recommendation.recommendation_data)
    
    # Get all cards to display their full details
    card_details = []
    for card_id, value_data in recommendation_data['card_details'].items():
        card = CreditCard.query.get(int(card_id))
        if card:
            card_details.append({
                'card': card,
                'estimated_value': value_data['estimated_value'],
                'category_values': value_data['category_values'],
                'signup_bonus_value': value_data['signup_bonus_value'],
                'net_value': value_data['net_value'],
                'signup_month': value_data['signup_month']
            })
    
    # Sort cards by net value (best first)
    card_details.sort(key=lambda x: x['net_value'], reverse=True)
    
    return render_template(
        'recommendations/show.html',
        recommendation=recommendation_data,
        profile=profile,
        category_spending=profile.get_category_spending(),
        card_details=card_details
    )

@recommendations.route('/history/<int:profile_id>')
def history(profile_id):
    """Show recommendation history for a profile."""
    profile = UserProfile.query.get_or_404(profile_id)
    recommendations_history = Recommendation.query.filter_by(user_profile_id=profile_id).order_by(Recommendation.created_at.desc()).all()
    
    return render_template(
        'recommendations/history.html',
        profile=profile,
        recommendations=recommendations_history
    ) 
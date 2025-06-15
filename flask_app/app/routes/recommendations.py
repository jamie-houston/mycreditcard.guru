from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import current_user
from app import db
from app.models.user_data import UserProfile
from app.models.recommendation import Recommendation
from app.models.credit_card import CreditCard
from app.engine.recommendation import RecommendationEngine
from app.utils.recommendation_engine import calculate_card_value
from datetime import datetime
import json
import uuid
import hashlib

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
@recommendations.route('/list')
def list():
    """List all recommendations for the current user or session."""
    if current_user.is_authenticated:
        user_id = current_user.id
        session_id = None
        profiles = {p.id: p for p in UserProfile.query.filter_by(user_id=user_id).all()}
    else:
        user_id = None
        if 'anonymous_user_id' not in session:
            session['anonymous_user_id'] = str(uuid.uuid4())
        session_id = session['anonymous_user_id']
        profiles = {p.id: p for p in UserProfile.query.filter_by(session_id=session_id).all()}
    recs = Recommendation.get_for_user_or_session(user_id=user_id, session_id=session_id)
    return render_template('recommendations/list.html', recommendations=recs, profiles=profiles)

@recommendations.route('/view/<int:recommendation_id>')
def view(recommendation_id):
    """Show recommendation details."""
    recommendation = Recommendation.query.get_or_404(recommendation_id)

    # Check if recommendation belongs to current user or session
    if current_user.is_authenticated:
        if recommendation.user_id != current_user.id:
            flash('You do not have permission to access this recommendation.', 'danger')
            return redirect(url_for('main.index'))
    else:
        if recommendation.session_id != session.get('anonymous_user_id'):
            flash('You do not have permission to access this recommendation.', 'danger')
            return redirect(url_for('main.index'))

    profile = UserProfile.query.get_or_404(recommendation.user_profile_id)

    # Get card details from the recommendation
    card_details = []
    for card_id, value_data in recommendation.card_details.items():
        card = db.session.get(CreditCard, int(card_id))
        if card:
            card_details.append({
                'card': card,
                'estimated_value': value_data['annual_value'],
                'category_values': {},  # Not provided in test data
                'signup_bonus_value': 0,  # Not provided in test data
                'net_value': value_data['annual_value'],
                'signup_month': 'Anytime'  # Not provided in test data
            })

    # Get category spending from profile
    category_spending = json.loads(profile.category_spending)

    # Create optimal strategy from recommended sequence
    optimal_strategy = [{'card_id': card_id, 'signup_month': 'Anytime'} for card_id in recommendation.recommended_sequence]

    return render_template(
        'recommendations/show.html',
        recommendation=recommendation,
        profile=profile,
        card_details=card_details,
        category_spending=category_spending,
        optimal_strategy=optimal_strategy
    )

@recommendations.route('/delete/<recommendation_id>', methods=['POST'])
def delete(recommendation_id):
    """Delete a recommendation by deterministic ID."""
    recommendation = Recommendation.query.filter_by(recommendation_id=recommendation_id).first_or_404()
    # Check if recommendation belongs to current user or session
    if current_user.is_authenticated:
        if recommendation.user_id != current_user.id:
            flash('You do not have permission to delete this recommendation.', 'danger')
            return redirect(url_for('main.index'))
    else:
        if recommendation.session_id != session.get('anonymous_user_id'):
            flash('You do not have permission to delete this recommendation.', 'danger')
            return redirect(url_for('main.index'))
    try:
        db.session.delete(recommendation)
        db.session.commit()
        flash('Recommendation deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting recommendation.', 'danger')
        current_app.logger.error(f'Error deleting recommendation: {str(e)}')
    return redirect(url_for('recommendations.list'))

@recommendations.route('/create/<int:profile_id>', methods=['GET', 'POST'])
def create(profile_id):
    """Generate credit card recommendations for a user profile."""
    # Get the user profile
    profile = UserProfile.query.get_or_404(profile_id)

    # Check if profile belongs to current user or session
    if current_user.is_authenticated:
        if profile.user_id != current_user.id:
            flash('You do not have permission to access this profile.', 'danger')
            return redirect(url_for('main.index'))
    else:
        if profile.session_id != session.get('anonymous_user_id'):
            flash('You do not have permission to access this profile.', 'danger')
            return redirect(url_for('main.index'))

    # if request.method == 'POST':
    try:
        # Get all credit cards from the database
        cards = CreditCard.query.all()

        # Generate recommendations
        recommendation_data = RecommendationEngine.generate_recommendations(profile, cards)

        # Store recommendation data in session to retrieve later
        session['recommendation_data'] = recommendation_data

        # Redirect to results page
        return redirect(url_for('recommendations.results', profile_id=profile.id))
    except Exception as e:
        flash(f'Error generating recommendations: {str(e)}', 'danger')
        # GET request - redirect to list view
        return redirect(url_for('recommendations.list'))
        # return redirect(url_for('recommendations.create', profile_id=profile.id))

def generate_recommendation_id(profile, recommendation_data):
    """Generate a deterministic hash for a recommendation based on profile and recommendation data."""
    # Normalize relevant data
    profile_data = {
        'credit_score': profile.credit_score,
        'income': profile.income,
        'total_monthly_spend': profile.total_monthly_spend,
        'category_spending': profile.get_category_spending(),
        'reward_preferences': profile.get_reward_preferences() if hasattr(profile, 'get_reward_preferences') else [],
        'max_cards': getattr(profile, 'max_cards', 5),
        'max_annual_fees': getattr(profile, 'max_annual_fees', None),
    }
    # Recommendation data (sort keys for determinism)
    rec_data = {
        'recommended_sequence': recommendation_data.get('recommended_sequence', []),
        'card_details': recommendation_data.get('card_details', {}),
        'total_value': recommendation_data.get('total_value', 0),
        'total_annual_fees': recommendation_data.get('total_annual_fees', 0),
        'per_month_value': recommendation_data.get('per_month_value', []),
    }
    # Serialize and hash
    hash_input = json.dumps({'profile': profile_data, 'recommendation': rec_data}, sort_keys=True)
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

@recommendations.route('/results/<recommendation_id>')
def results_by_id(recommendation_id):
    """Show recommendation results by deterministic, shareable ID."""
    recommendation = Recommendation.query.filter_by(recommendation_id=recommendation_id).first()
    if not recommendation:
        flash('No recommendation found for this ID. Please generate a new recommendation.', 'warning')
        return redirect(url_for('user_data.profile'))
    
    profile = UserProfile.query.get_or_404(recommendation.user_profile_id)
    card_ids = recommendation.recommended_sequence
    cards = {}
    for card_id in card_ids:
        card = db.session.get(CreditCard, card_id)
        if card:
            cards[card_id] = card
    
    category_totals = {}
    card_details = recommendation.card_details
    
    # For each category, find the card with the highest reward value for that category
    # This prevents double-counting rewards across multiple cards
    all_categories = set()
    for card_id in card_ids:
        details = card_details.get(str(card_id), {})
        rewards_by_category = details.get('rewards_by_category', {})
        all_categories.update(rewards_by_category.keys())
    
    for category in all_categories:
        if category == 'signup_bonus':
            continue  # Skip signup bonus in category totals
        max_value = 0
        for card_id in card_ids:
            details = card_details.get(str(card_id), {})
            rewards_by_category = details.get('rewards_by_category', {})
            reward_info = rewards_by_category.get(category, {})
            if isinstance(reward_info, dict) and 'value' in reward_info:
                value = reward_info['value'] / 12  # Convert annual to monthly
                if value > max_value:
                    max_value = value
        if max_value > 0:
            category_totals[category] = max_value
    
    return render_template(
        'recommendations/results.html',
        profile=profile,
        recommendation=recommendation,
        cards=cards,
        category_totals=category_totals
    )

@recommendations.route('/generate', methods=['POST'])
def generate():
    """Generate recommendations based on form data."""
    try:
        # Get form data
        credit_score = int(request.form.get('credit_score', 700))
        income = float(request.form.get('income', 50000))
        max_cards = int(request.form.get('max_cards', 1))
        max_annual_fees = float(request.form.get('max_annual_fees', 0))
        
        # Get category spending
        categories = Category.get_active_categories()
        category_spending = {}
        total_monthly_spend = 0
        
        for category in categories:
            amount = float(request.form.get(f'category_{category.name}', 0))
            category_spending[category.name] = amount
            total_monthly_spend += amount
        
        # Get reward preferences
        reward_preferences = request.form.getlist('reward_preferences')
        
        # Create a temporary profile for recommendation generation
        profile_data = {
            'credit_score': credit_score,
            'income': income,
            'total_monthly_spend': total_monthly_spend,
            'category_spending': category_spending,
            'reward_preferences': reward_preferences,
            'max_cards': max_cards,
            'max_annual_fees': max_annual_fees
        }
        
        # Create a temporary profile object
        class TempProfile:
            def __init__(self, data):
                self.credit_score = data['credit_score']
                self.income = data['income']
                self.total_monthly_spend = data['total_monthly_spend']
                self.max_cards = data['max_cards']
                self.max_annual_fees = data['max_annual_fees']
                self._category_spending = data['category_spending']
                self._reward_preferences = data['reward_preferences']
            
            def get_category_spending(self):
                return self._category_spending
            
            def get_reward_preferences(self):
                return self._reward_preferences
        
        temp_profile = TempProfile(profile_data)
        
        # Generate recommendation ID for this profile
        recommendation_id = hashlib.sha256(
            json.dumps(profile_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        
        # Generate recommendations
        cards = CreditCard.query.all()
        recommendation_data = RecommendationEngine.generate_recommendations(temp_profile, cards)
        
        # Store in session for display (not DB)
        session['recommendation_data'] = recommendation_data
        session['recommendation_id'] = recommendation_id
        
        return redirect(url_for('recommendations.results_by_id', recommendation_id=recommendation_id))
        
    except Exception as e:
        flash(f'Error generating recommendations: {str(e)}', 'danger')
        return redirect(url_for('user_data.profile'))

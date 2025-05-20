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
    # Get the anonymous user ID from session if not authenticated
    if current_user.is_authenticated:
        user_id = current_user.id
        session_id = None
    else:
        user_id = None
        if 'anonymous_user_id' not in session:
            session['anonymous_user_id'] = str(uuid.uuid4())
        session_id = session['anonymous_user_id']

    # Get recommendations for either the logged-in user or the anonymous session
    recs = Recommendation.get_for_user_or_session(user_id=user_id, session_id=session_id)

    return render_template('recommendations/list.html', recommendations=recs)

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
        card = CreditCard.query.get(int(card_id))
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

@recommendations.route('/delete/<int:recommendation_id>', methods=['POST'])
def delete(recommendation_id):
    """Delete a recommendation."""
    recommendation = Recommendation.query.get_or_404(recommendation_id)

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


@recommendations.route('/results/<int:profile_id>')
def results(profile_id: int):
    """Show recommendation results for a user profile."""
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

    # Get recommendation data from session
    recommendation_data = session.get('recommendation_data')

    if not recommendation_data:
        flash('No recommendation data found. Please generate recommendations first.', 'warning')
        return redirect(url_for('recommendations.create', profile_id=profile.id))

    # Get cards for the recommendation
    card_ids = recommendation_data.get('recommended_sequence', [])
    cards = {}
    for card_id in card_ids:
        card = CreditCard.query.get(card_id)
        if card:
            cards[card_id] = card

    # Render the results template
    return render_template(
        'recommendations/results.html',
        profile=profile,
        recommendation=recommendation_data,
        cards=cards
    )

@recommendations.route('/save/<int:profile_id>', methods=['POST'])
def save(profile_id: int):
    """Save a recommendation to the database."""
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

    # Get recommendation data from session
    recommendation_data = session.get('recommendation_data')

    if not recommendation_data:
        flash('No recommendation data found. Please generate recommendations first.', 'warning')
        return redirect(url_for('recommendations.create', profile_id=profile.id))

    # Create a new recommendation
    try:
        recommendation = Recommendation()
        recommendation.user_profile_id = profile.id

        # Set user_id or session_id based on authentication status
        if current_user.is_authenticated:
            recommendation.user_id = current_user.id
        else:
            recommendation.session_id = session.get('anonymous_user_id')

        # Set recommendation data
        recommendation.spending_profile = recommendation_data.get('spending_profile', {})
        recommendation.card_preferences = recommendation_data.get('card_preferences', {})
        recommendation.recommended_sequence = recommendation_data.get('recommended_sequence', [])
        recommendation.card_details = recommendation_data.get('card_details', {})
        recommendation.total_value = recommendation_data.get('total_value', 0)
        recommendation.total_annual_fees = recommendation_data.get('total_annual_fees', 0)
        recommendation.per_month_value = recommendation_data.get('per_month_value', [])
        recommendation.card_count = len(recommendation_data.get('recommended_sequence', []))

        db.session.add(recommendation)
        db.session.commit()

        flash('Recommendation saved successfully!', 'success')
        return redirect(url_for('recommendations.view', recommendation_id=recommendation.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving recommendation: {str(e)}', 'danger')
        current_app.logger.error(f'Error saving recommendation: {str(e)}')
        return redirect(url_for('recommendations.results', profile_id=profile.id))

@recommendations.route('/compare/<int:profile_id>')
def compare(profile_id: int):
    """Compare multiple recommendation strategies."""
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
        'cashback_focused': RecommendationEngine.generate_recommendations(profile, [c for c in cards if c.reward_type == 'cashback']),
        'travel_focused': RecommendationEngine.generate_recommendations(profile, [c for c in cards if c.reward_type == 'travel']),
        'no_annual_fee': RecommendationEngine.generate_recommendations(profile, [c for c in cards if c.annual_fee == 0])
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

@recommendations.route('/history/<int:profile_id>')
def history(profile_id):
    """Show recommendation history for a profile."""
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

    # Get all recommendations for this profile
    recommendations = Recommendation.query.filter_by(user_profile_id=profile_id).order_by(Recommendation.created_at.desc()).all()

    return render_template(
        'recommendations/history.html',
        profile=profile,
        recommendations=recommendations
    )

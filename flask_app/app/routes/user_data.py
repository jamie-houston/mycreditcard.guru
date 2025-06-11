from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import current_user
from app import db
from app.models.user_data import UserProfile
from app.models.category import Category
from marshmallow import Schema, fields, ValidationError
import json
import uuid

user_data = Blueprint('user_data', __name__)

class UserProfileSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    credit_score = fields.Int(required=True)
    income = fields.Float(required=True)
    total_monthly_spend = fields.Float(required=True)
    category_spending = fields.Str(dump_default='{}')
    reward_preferences = fields.Str(dump_default='[]')
    max_annual_fees = fields.Float()
    max_cards = fields.Int()

@user_data.route('/profile', methods=['GET', 'POST'])
def profile():
    """User profile form to collect spending habits and preferences."""
    if request.method == 'POST':
        try:
            # Process category spending from form
            category_spending = {}
            for key, value in request.form.items():
                if key.startswith('category_') and value:
                    category = key.replace('category_', '')
                    try:
                        amount = float(value)
                        if amount > 0:  # Only include non-zero values
                            category_spending[category] = amount
                    except ValueError:
                        pass

            # Calculate total monthly spend from category spending
            total_monthly_spend = sum(category_spending.values())

            # Process reward preferences from form
            reward_preferences = request.form.getlist('reward_preferences')

            # Get other form data
            profile_name = request.form.get('profile_name', 'My Spending Profile')
            credit_score = int(request.form.get('credit_score', 700))
            income = float(request.form.get('income', 50000))
            max_cards = int(request.form.get('max_cards', 5))
            max_annual_fees = float(request.form.get('max_annual_fees', 0))

            # Create or update profile in the database
            if current_user.is_authenticated:
                # For logged-in users, get their existing profile or create a new one
                profile = UserProfile.query.filter_by(user_id=current_user.id).first()
                is_new_profile = profile is None

                if not profile:
                    profile = UserProfile(user_id=current_user.id)
            else:
                # For anonymous users, store a session ID and get/create profile for that session
                if 'anonymous_user_id' not in session:
                    session['anonymous_user_id'] = str(uuid.uuid4())

                session_id = session['anonymous_user_id']
                profile = UserProfile.query.filter_by(session_id=session_id).first()
                is_new_profile = profile is None

                if not profile:
                    profile = UserProfile(session_id=session_id)

            # Update profile fields
            profile.name = profile_name
            profile.credit_score = credit_score
            profile.income = income
            profile.total_monthly_spend = total_monthly_spend
            profile.category_spending = json.dumps(category_spending)
            profile.reward_preferences = json.dumps(reward_preferences)
            profile.max_cards = max_cards
            profile.max_annual_fees = max_annual_fees

            # Save to database
            db.session.add(profile)
            db.session.commit()

            if len(category_spending) > 0:
                flash(f'Spending profile saved successfully! Click on "Generate Recommendations" to see your personalized credit card suggestions.', 'success')
            else:
                flash(f'Profile saved, but you need to enter some spending data to generate recommendations.', 'warning')

            return redirect(url_for('user_data.profile'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving profile: {str(e)}")
            flash(f'Error saving profile: {str(e)}', 'danger')

    # GET request - show the profile form
    # Get categories from database instead of hardcoded config
    db_categories = Category.get_active_categories()
    categories = [cat.name for cat in db_categories]
    category_descriptions = {cat.name: cat.description for cat in db_categories}

    reward_options = current_app.config.get('REWARD_OPTIONS', [
        'cash_back', 'travel_points', 'airline_miles',
        'hotel_points', 'statement_credits', 'shopping_benefits'
    ])

    reward_descriptions = current_app.config.get('REWARD_DESCRIPTIONS', {
        'cash_back': 'Direct cash rewards as statement credits or deposits',
        'travel_points': 'Flexible points that can be redeemed for travel bookings',
        'airline_miles': 'Miles that can be used for flight redemptions',
        'hotel_points': 'Points that can be redeemed for hotel stays',
        'statement_credits': 'Credits for specific categories like dining or travel',
        'shopping_benefits': 'Special discounts, extended warranties, and purchase protection'
    })

    # Get the user's profile if they have one
    if current_user.is_authenticated:
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    else:
        session_id = session.get('anonymous_user_id')
        profile = UserProfile.query.filter_by(session_id=session_id).first() if session_id else None

    # Parse category spending and reward preferences if profile exists
    category_spending = json.loads(profile.category_spending) if profile else {}
    reward_preferences = json.loads(profile.reward_preferences) if profile and profile.reward_preferences else []

    return render_template(
        'user_data/profile.html',
        profile=profile,
        categories=db_categories,  # Pass full category objects instead of just names
        category_descriptions=category_descriptions,
        category_spending=category_spending,
        reward_options=reward_options,
        reward_descriptions=reward_descriptions,
        reward_preferences=reward_preferences
    )

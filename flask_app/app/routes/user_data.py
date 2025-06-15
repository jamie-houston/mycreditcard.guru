from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import current_user
from app import db
from app.models.user_data import UserProfile
from app.models.category import Category
from app.models.credit_card import CardIssuer
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
    reward_type = fields.Str(dump_default='points')
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

            # Process reward type from form
            reward_type = request.form.get('reward_type', 'points')

            # Get other form data
            profile_name = request.form.get('profile_name', 'My Spending Profile')
            credit_score = int(request.form.get('credit_score', 700))
            income = float(request.form.get('income', 50000))
            max_cards = int(request.form.get('max_cards', 1))
            max_annual_fees_raw = request.form.get('max_annual_fees')
            if max_annual_fees_raw and max_annual_fees_raw.strip() != '':
                max_annual_fees = float(max_annual_fees_raw)
            else:
                max_annual_fees = None
            preferred_issuer_id = request.form.get('preferred_issuer_id')
            if preferred_issuer_id == '':  # Convert empty string to None
                preferred_issuer_id = None
            elif preferred_issuer_id:
                preferred_issuer_id = int(preferred_issuer_id)

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
            profile.reward_type = reward_type
            profile.max_cards = max_cards
            profile.max_annual_fees = max_annual_fees
            profile.preferred_issuer_id = preferred_issuer_id

            # Save to database
            db.session.add(profile)
            db.session.commit()

            # Check what action the user wants to take
            action = request.form.get('action', 'save_profile')
            
            if action == 'generate_recommendations':
                if len(category_spending) > 0:
                    flash(f'Spending profile saved successfully! Generating your personalized recommendations...', 'success')
                    return redirect(url_for('recommendations.create', profile_id=profile.id))
                else:
                    flash(f'Profile saved, but you need to enter some spending data to generate meaningful recommendations.', 'warning')
                    return redirect(url_for('user_data.profile'))
            else:
                # Regular save without generating recommendations
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
    db_categories = Category.get_active_categories()
    categories = [cat.name for cat in db_categories]
    category_descriptions = {cat.name: cat.description for cat in db_categories}
    
    # Get all issuers for the dropdown
    issuers = CardIssuer.all_ordered()

    # Get the user's profile if they have one
    if current_user.is_authenticated:
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    else:
        session_id = session.get('anonymous_user_id')
        profile = UserProfile.query.filter_by(session_id=session_id).first() if session_id else None

    # Prefill from query params if present
    prefill = request.args
    if prefill:
        # Build category_spending from category_* params
        category_spending = {}
        for cat in categories:
            val = prefill.get(f'category_{cat}')
            if val is not None:
                try:
                    val = float(val)
                    if val > 0:
                        category_spending[cat] = val
                except ValueError:
                    pass
        # Other fields
        credit_score = int(prefill.get('credit_score', profile.credit_score if profile else 700))
        income = float(prefill.get('income', profile.income if profile else 50000))
        max_cards = int(prefill.get('max_cards', profile.max_cards if profile else 1))
        max_annual_fees_raw = prefill.get('max_annual_fees')
        if max_annual_fees_raw is not None and max_annual_fees_raw != '':
            max_annual_fees = float(max_annual_fees_raw)
        else:
            max_annual_fees = None
        reward_type = prefill.get('reward_type', profile.reward_type if profile else 'points')
    else:
        category_spending = json.loads(profile.category_spending) if profile else {}
        credit_score = profile.credit_score if profile else 700
        income = profile.income if profile else 50000
        max_cards = profile.max_cards if profile else 1
        max_annual_fees = profile.max_annual_fees if profile else None
        reward_type = profile.reward_type if profile else 'points'

    return render_template(
        'user_data/profile.html',
        profile=profile,
        categories=db_categories,  # Pass full category objects instead of just names
        category_descriptions=category_descriptions,
        category_spending=category_spending,
        reward_type=reward_type,
        credit_score=credit_score,
        income=income,
        max_cards=max_cards,
        max_annual_fees=max_annual_fees,
        issuers=issuers
    )

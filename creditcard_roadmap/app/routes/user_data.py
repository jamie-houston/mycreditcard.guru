from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.user_data import UserProfile
from marshmallow import Schema, fields, ValidationError
import json

user_data = Blueprint('user_data', __name__)

class UserProfileSchema(Schema):
    id = fields.Int(dump_only=True)
    total_monthly_spend = fields.Float(required=True)
    category_spending = fields.Str(default='{}')
    reward_preferences = fields.Str(default='[]')
    max_annual_fees = fields.Float()
    max_cards = fields.Int()

@user_data.route('/profile', methods=['GET', 'POST'])
def profile():
    """User profile form to collect spending habits and preferences."""
    if request.method == 'POST':
        try:
            # Get form data and validate
            data = {
                'total_monthly_spend': float(request.form.get('total_monthly_spend', 0)),
                'max_annual_fees': float(request.form.get('max_annual_fees', 0)),
                'max_cards': int(request.form.get('max_cards', 5)),
            }
            
            # Process category spending from form
            category_spending = {}
            for key, value in request.form.items():
                if key.startswith('category_') and value:
                    category = key.replace('category_', '')
                    try:
                        category_spending[category] = float(value)
                    except ValueError:
                        flash(f'Invalid value for {category}', 'danger')
                        return render_template('user_data/profile.html')
            
            data['category_spending'] = json.dumps(category_spending)
            
            # Process reward preferences
            data['reward_preferences'] = json.dumps(request.form.getlist('reward_preferences'))
            
            # Validate with schema
            schema = UserProfileSchema()
            validated_data = schema.load(data)
            
            # Create or update user profile
            profile_id = session.get('profile_id')
            if profile_id:
                profile = UserProfile.query.get(profile_id)
                if profile:
                    for key, value in validated_data.items():
                        setattr(profile, key, value)
                else:
                    profile = UserProfile(**validated_data)
                    db.session.add(profile)
            else:
                profile = UserProfile(**validated_data)
                db.session.add(profile)
            
            db.session.commit()
            session['profile_id'] = profile.id
            
            flash('Profile data saved successfully!', 'success')
            return redirect(url_for('recommendations.generate'))
        
        except ValidationError as e:
            flash('Validation error: ' + str(e.messages), 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # Check for existing profile
    profile = None
    profile_id = session.get('profile_id')
    if profile_id:
        profile = UserProfile.query.get(profile_id)
    
    # Define common spending categories for the form
    categories = [
        'groceries', 'dining', 'gas', 'travel', 'entertainment', 
        'shopping', 'utilities', 'healthcare', 'other'
    ]
    
    # Define reward preferences options
    reward_options = [
        'cash_back', 'travel_points', 'airline_miles', 'hotel_points', 
        'statement_credits', 'shopping_benefits'
    ]
    
    # Parse stored JSON data if profile exists
    category_spending = {}
    reward_preferences = []
    if profile:
        try:
            category_spending = json.loads(profile.category_spending)
            reward_preferences = json.loads(profile.reward_preferences)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return render_template('user_data/profile.html', 
                          profile=profile, 
                          categories=categories,
                          reward_options=reward_options,
                          category_spending=category_spending,
                          reward_preferences=reward_preferences) 
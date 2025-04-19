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
                        amount = float(value)
                        if amount > 0:  # Only include non-zero values
                            category_spending[category] = amount
                    except ValueError:
                        flash(f'Invalid value for {category}', 'danger')
                        return render_template('user_data/profile.html')
            
            data['category_spending'] = json.dumps(category_spending)
            
            # Process reward preferences
            data['reward_preferences'] = json.dumps(request.form.getlist('reward_preferences'))
            
            # Calculate spending summary
            total_categorized = sum(category_spending.values())
            if total_categorized > data['total_monthly_spend'] * 1.1:
                flash('Warning: Your category spending exceeds your total monthly spending. Please check your numbers.', 'warning')
            elif total_categorized < data['total_monthly_spend'] * 0.5 and total_categorized > 0:
                flash('Tip: You have a large portion of uncategorized spending. Adding more category details will improve your recommendations.', 'info')
            
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
    
    # Define common spending categories for the form with descriptions
    categories = [
        'groceries', 'dining', 'gas', 'travel', 'entertainment', 
        'shopping', 'utilities', 'healthcare', 'transportation', 'education', 'other'
    ]
    
    category_descriptions = {
        'groceries': 'Supermarkets, grocery stores, and specialty food shops',
        'dining': 'Restaurants, cafes, takeout, and food delivery services',
        'gas': 'Gas stations and fuel purchases',
        'travel': 'Airlines, hotels, rental cars, and vacation expenses',
        'entertainment': 'Movies, concerts, streaming subscriptions, and recreation',
        'shopping': 'Retail stores, online shopping, and department stores',
        'utilities': 'Electricity, water, gas, internet, phone, and other utility bills',
        'healthcare': 'Medical expenses, prescriptions, and insurance payments',
        'transportation': 'Public transit, rideshare services, and vehicle maintenance',
        'education': 'Tuition, books, courses, and education-related expenses',
        'other': 'Any expenses that don\'t fit into the above categories'
    }
    
    # Define reward preferences options with descriptions
    reward_options = [
        'cash_back', 'travel_points', 'airline_miles', 'hotel_points', 
        'statement_credits', 'shopping_benefits'
    ]
    
    reward_descriptions = {
        'cash_back': 'Direct cash rewards as statement credits or deposits',
        'travel_points': 'Flexible points that can be redeemed for travel bookings',
        'airline_miles': 'Miles that can be used for flight redemptions',
        'hotel_points': 'Points that can be redeemed for hotel stays',
        'statement_credits': 'Credits for specific categories like dining or travel',
        'shopping_benefits': 'Special discounts, extended warranties, and purchase protection'
    }
    
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
                          category_descriptions=category_descriptions,
                          reward_options=reward_options,
                          reward_descriptions=reward_descriptions,
                          category_spending=category_spending,
                          reward_preferences=reward_preferences) 
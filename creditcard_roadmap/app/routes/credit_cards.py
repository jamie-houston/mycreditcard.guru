from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.credit_card import CreditCard
from marshmallow import Schema, fields, ValidationError
from app.utils.card_scraper import scrape_credit_cards
import json

credit_cards = Blueprint('credit_cards', __name__)

class CreditCardSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    issuer = fields.Str(required=True)
    annual_fee = fields.Float(default=0.0)
    reward_categories = fields.Str(default='[]')
    offers = fields.Str(default='[]')
    signup_bonus_points = fields.Int(default=0)
    signup_bonus_value = fields.Float(default=0.0)
    signup_bonus_spend_requirement = fields.Float(default=0.0)
    signup_bonus_time_period = fields.Int(default=3)

@credit_cards.route('/')
def index():
    """List all credit cards."""
    cards = CreditCard.query.all()
    return render_template('credit_cards/index.html', cards=cards)

@credit_cards.route('/import', methods=['GET', 'POST'])
def import_cards():
    """Import credit cards from web scraping."""
    if request.method == 'POST':
        try:
            # Get scraping source from form
            source = request.form.get('source', 'nerdwallet')
            
            # Scrape credit cards data
            if source == 'nerdwallet':
                cards_data = scrape_credit_cards()
                
                if not cards_data:
                    flash('No credit cards found to import', 'warning')
                    return render_template('credit_cards/import.html')
                
                # Import each card to database
                imported_count = 0
                for card_data in cards_data:
                    # Convert list/dict fields to JSON strings
                    if 'reward_categories' in card_data:
                        card_data['reward_categories'] = json.dumps(card_data['reward_categories'])
                    if 'offers' in card_data:
                        card_data['offers'] = json.dumps(card_data['offers'])
                    
                    # Check if card already exists by name and issuer
                    existing_card = CreditCard.query.filter_by(
                        name=card_data['name'],
                        issuer=card_data['issuer']
                    ).first()
                    
                    if existing_card:
                        # Update existing card
                        for key, value in card_data.items():
                            setattr(existing_card, key, value)
                    else:
                        # Create new card
                        card = CreditCard(**card_data)
                        db.session.add(card)
                    
                    imported_count += 1
                
                db.session.commit()
                flash(f'Successfully imported {imported_count} credit cards!', 'success')
                return redirect(url_for('credit_cards.index'))
            
            else:
                flash('Unsupported data source', 'danger')
                return render_template('credit_cards/import.html')
                
        except Exception as e:
            flash(f'Error importing credit cards: {str(e)}', 'danger')
            return render_template('credit_cards/import.html')
    
    return render_template('credit_cards/import.html')

@credit_cards.route('/new', methods=['GET', 'POST'])
def new():
    """Add a new credit card."""
    if request.method == 'POST':
        try:
            # Extract basic card details
            data = {
                'name': request.form.get('name'),
                'issuer': request.form.get('issuer'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'signup_bonus_points': int(request.form.get('signup_bonus_points', 0)),
                'signup_bonus_value': float(request.form.get('signup_bonus_value', 0)),
                'signup_bonus_spend_requirement': float(request.form.get('signup_bonus_spend_requirement', 0)),
                'signup_bonus_time_period': int(request.form.get('signup_bonus_time_period', 3)),
            }
            
            # Process reward categories from form
            reward_categories = []
            category_indices = set()
            
            for key in request.form:
                if key.startswith('category_name_'):
                    idx = key.replace('category_name_', '')
                    category_indices.add(idx)
            
            for idx in category_indices:
                category_name = request.form.get(f'category_name_{idx}')
                category_percentage = request.form.get(f'category_percentage_{idx}')
                
                if category_name and category_percentage:
                    try:
                        reward_categories.append({
                            'category': category_name,
                            'percentage': float(category_percentage)
                        })
                    except ValueError:
                        flash(f'Invalid percentage for {category_name}', 'danger')
                        return render_template('credit_cards/new.html')
            
            data['reward_categories'] = json.dumps(reward_categories)
            
            # Process offers from form
            offers = []
            offer_indices = set()
            
            for key in request.form:
                if key.startswith('offer_type_'):
                    idx = key.replace('offer_type_', '')
                    offer_indices.add(idx)
            
            for idx in offer_indices:
                offer_type = request.form.get(f'offer_type_{idx}')
                offer_amount = request.form.get(f'offer_amount_{idx}')
                offer_frequency = request.form.get(f'offer_frequency_{idx}')
                
                if offer_type and offer_amount:
                    try:
                        offers.append({
                            'type': offer_type,
                            'amount': float(offer_amount),
                            'frequency': offer_frequency or 'one_time'
                        })
                    except ValueError:
                        flash(f'Invalid amount for {offer_type}', 'danger')
                        return render_template('credit_cards/new.html')
            
            data['offers'] = json.dumps(offers)
            
            # Validate and create credit card
            schema = CreditCardSchema()
            validated_data = schema.load(data)
            
            credit_card = CreditCard(**validated_data)
            db.session.add(credit_card)
            db.session.commit()
            
            flash('Credit card added successfully!', 'success')
            return redirect(url_for('credit_cards.index'))
        except ValidationError as e:
            flash('Validation error: ' + str(e.messages), 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('credit_cards/new.html')

@credit_cards.route('/<int:id>')
def show(id):
    """Show a single credit card."""
    card = CreditCard.query.get_or_404(id)
    
    # Parse JSON data
    try:
        reward_categories = json.loads(card.reward_categories)
        offers = json.loads(card.offers)
    except (json.JSONDecodeError, TypeError):
        reward_categories = []
        offers = []
    
    return render_template('credit_cards/show.html', 
                          card=card, 
                          reward_categories=reward_categories,
                          offers=offers)

@credit_cards.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit a credit card."""
    card = CreditCard.query.get_or_404(id)
    
    # Parse JSON data for display
    try:
        reward_categories = json.loads(card.reward_categories)
        offers = json.loads(card.offers)
    except (json.JSONDecodeError, TypeError):
        reward_categories = []
        offers = []
    
    if request.method == 'POST':
        try:
            # Similar processing as in the 'new' route
            data = {
                'name': request.form.get('name'),
                'issuer': request.form.get('issuer'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'signup_bonus_points': int(request.form.get('signup_bonus_points', 0)),
                'signup_bonus_value': float(request.form.get('signup_bonus_value', 0)),
                'signup_bonus_spend_requirement': float(request.form.get('signup_bonus_spend_requirement', 0)),
                'signup_bonus_time_period': int(request.form.get('signup_bonus_time_period', 3)),
            }
            
            # Process reward categories (similar to 'new' route)
            reward_categories = []
            category_indices = set()
            
            for key in request.form:
                if key.startswith('category_name_'):
                    idx = key.replace('category_name_', '')
                    category_indices.add(idx)
            
            for idx in category_indices:
                category_name = request.form.get(f'category_name_{idx}')
                category_percentage = request.form.get(f'category_percentage_{idx}')
                
                if category_name and category_percentage:
                    reward_categories.append({
                        'category': category_name,
                        'percentage': float(category_percentage)
                    })
            
            data['reward_categories'] = json.dumps(reward_categories)
            
            # Process offers (similar to 'new' route)
            offers = []
            offer_indices = set()
            
            for key in request.form:
                if key.startswith('offer_type_'):
                    idx = key.replace('offer_type_', '')
                    offer_indices.add(idx)
            
            for idx in offer_indices:
                offer_type = request.form.get(f'offer_type_{idx}')
                offer_amount = request.form.get(f'offer_amount_{idx}')
                offer_frequency = request.form.get(f'offer_frequency_{idx}')
                
                if offer_type and offer_amount:
                    offers.append({
                        'type': offer_type,
                        'amount': float(offer_amount),
                        'frequency': offer_frequency or 'one_time'
                    })
            
            data['offers'] = json.dumps(offers)
            
            # Validate and update
            schema = CreditCardSchema()
            validated_data = schema.load(data)
            
            # Update card with new data
            for key, value in validated_data.items():
                setattr(card, key, value)
            
            db.session.commit()
            flash('Credit card updated successfully!', 'success')
            return redirect(url_for('credit_cards.show', id=id))
        except ValidationError as e:
            flash('Validation error: ' + str(e.messages), 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('credit_cards/edit.html', 
                          card=card,
                          reward_categories=reward_categories,
                          offers=offers)

@credit_cards.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a credit card."""
    card = CreditCard.query.get_or_404(id)
    db.session.delete(card)
    db.session.commit()
    
    flash('Credit card deleted successfully!', 'success')
    return redirect(url_for('credit_cards.index')) 
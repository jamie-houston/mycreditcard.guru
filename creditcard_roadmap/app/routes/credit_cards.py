from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.credit_card import CreditCard
from marshmallow import Schema, fields, ValidationError
from app.utils.card_scraper import scrape_credit_cards
from app.utils.data_utils import map_scraped_card_to_model
import json

credit_cards = Blueprint('credit_cards', __name__)

class CreditCardSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    issuer = fields.Str(required=True)
    annual_fee = fields.Float(default=0.0)
    reward_categories = fields.Str(default='[]')
    special_offers = fields.Str(default='[]')
    signup_bonus_points = fields.Int(default=0)
    signup_bonus_value = fields.Float(default=0.0)
    signup_bonus_min_spend = fields.Float(default=0.0)
    signup_bonus_time_limit = fields.Int(default=3)

@credit_cards.route('/')
def index():
    """List all credit cards."""
    cards = CreditCard.query.all()
    return render_template('credit_cards/index.html', cards=cards)

@credit_cards.route('/import', methods=['GET', 'POST'])
def import_cards():
    """Import credit cards from a data source"""
    if request.method == 'POST':
        source = request.form.get('source', 'nerdwallet')
        try:
            # Scrape credit cards from the source
            cards_data = scrape_credit_cards(source)
            
            # Create new cards from the scraped data
            for card_data in cards_data:
                # Map field names from scraper to model fields
                mapped_data = map_scraped_card_to_model(card_data)
                
                # Check if card already exists
                existing_card = CreditCard.query.filter_by(name=mapped_data['name']).first()
                if existing_card:
                    # Update existing card
                    for key, value in mapped_data.items():
                        if key in ['reward_categories', 'special_offers'] and isinstance(value, list):
                            setattr(existing_card, key, json.dumps(value))
                        else:
                            setattr(existing_card, key, value)
                else:
                    # Create new card
                    new_card = CreditCard(**mapped_data)
                    db.session.add(new_card)
            
            db.session.commit()
            flash(f"Successfully imported {len(cards_data)} credit cards from {source}.", "success")
            return redirect(url_for('credit_cards.index'))
        
        except Exception as e:
            db.session.rollback()
            error_message = f"Error importing credit cards: {str(e)}"
            flash(error_message, "danger")
            print(error_message)
    
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
                'signup_bonus_min_spend': float(request.form.get('signup_bonus_min_spend', 0)),
                'signup_bonus_time_limit': int(request.form.get('signup_bonus_time_limit', 3)),
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
            
            # Process special offers from form
            special_offers = []
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
                        special_offers.append({
                            'type': offer_type,
                            'amount': float(offer_amount),
                            'frequency': offer_frequency or 'one_time'
                        })
                    except ValueError:
                        flash(f'Invalid amount for {offer_type}', 'danger')
                        return render_template('credit_cards/new.html')
            
            data['special_offers'] = json.dumps(special_offers)
            
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
        special_offers = json.loads(card.special_offers)
    except (json.JSONDecodeError, TypeError):
        reward_categories = []
        special_offers = []
    
    return render_template('credit_cards/show.html', 
                          card=card, 
                          reward_categories=reward_categories,
                          special_offers=special_offers)

@credit_cards.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit a credit card."""
    card = CreditCard.query.get_or_404(id)
    
    # Parse JSON data for display
    try:
        reward_categories = json.loads(card.reward_categories)
        special_offers = json.loads(card.special_offers)
    except (json.JSONDecodeError, TypeError):
        reward_categories = []
        special_offers = []
    
    if request.method == 'POST':
        try:
            # Similar processing as in the 'new' route
            data = {
                'name': request.form.get('name'),
                'issuer': request.form.get('issuer'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'signup_bonus_points': int(request.form.get('signup_bonus_points', 0)),
                'signup_bonus_value': float(request.form.get('signup_bonus_value', 0)),
                'signup_bonus_min_spend': float(request.form.get('signup_bonus_min_spend', 0)),
                'signup_bonus_time_limit': int(request.form.get('signup_bonus_time_limit', 3)),
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
            
            # Process special offers (similar to 'new' route)
            special_offers = []
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
                    special_offers.append({
                        'type': offer_type,
                        'amount': float(offer_amount),
                        'frequency': offer_frequency or 'one_time'
                    })
            
            data['special_offers'] = json.dumps(special_offers)
            
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
                          special_offers=special_offers)

@credit_cards.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a credit card."""
    card = CreditCard.query.get_or_404(id)
    db.session.delete(card)
    db.session.commit()
    
    flash('Credit card deleted successfully!', 'success')
    return redirect(url_for('credit_cards.index')) 
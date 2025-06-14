from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user, login_required
from app import db
from app.models.credit_card import CreditCard
from marshmallow import Schema, fields, ValidationError
from app.utils.card_scraper import scrape_credit_cards, SOURCE_URLS
from app.utils.data_utils import map_scraped_card_to_model
from app.utils.compat import safe_query, safe_commit
import json
from datetime import datetime
from flask_wtf import FlaskForm
from app.models import CreditCard, Category, CreditCardReward, CardIssuer

credit_cards = Blueprint('credit_cards', __name__)

# Admin access decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('credit_cards.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

class CreditCardSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    issuer = fields.Str(required=True)
    annual_fee = fields.Float(dump_default=0.0)
    reward_categories = fields.Str(dump_default='[]')
    special_offers = fields.Str(dump_default='[]')
    signup_bonus_points = fields.Int(dump_default=0)
    signup_bonus_value = fields.Float(dump_default=0.0)
    signup_bonus_min_spend = fields.Float(dump_default=0.0)
    signup_bonus_time_limit = fields.Int(dump_default=3)
    signup_bonus_type = fields.Str(dump_default='points')

@credit_cards.route('/')
def index():
    """List all credit cards."""
    cards = safe_query(CreditCard).all()
    
    # Get bonus categories for each card (categories with rewards > 1%)
    cards_bonus_categories = {}
    from app.models.category import Category, CreditCardReward
    
    for card in cards:
        # Get all rewards for this card that are > 1%
        bonus_rewards = db.session.query(CreditCardReward, Category).join(
            Category, CreditCardReward.category_id == Category.id
        ).filter(
            CreditCardReward.credit_card_id == card.id,
            CreditCardReward.reward_percent > 1.0,
            Category.is_active == True
        ).order_by(CreditCardReward.reward_percent.desc()).all()
        
        # Format the bonus categories with their percentages
        formatted_categories = []
        for reward, category in bonus_rewards:
            formatted_categories.append({
                'name': category.display_name,
                'percent': reward.reward_percent,
                'icon': category.icon
            })
        
        cards_bonus_categories[card.id] = formatted_categories
    
    return render_template('credit_cards/index.html', 
                          cards=cards, 
                          cards_bonus_categories=cards_bonus_categories)

@credit_cards.route('/import', methods=['GET', 'POST'])
@admin_required
def import_cards():
    """Import credit cards from a data source"""
    if request.method == 'POST':
        source = request.form.get('source', 'nerdwallet')
        try:
            # Scrape credit cards from the source
            cards_data = scrape_credit_cards(source)
            
            # Set source URLs based on the source
            source_url = SOURCE_URLS.get(source, '')
            import_date = datetime.utcnow()
            
            # Create new cards from the scraped data
            with safe_commit():  # Use the safe commit context manager
                for card_data in cards_data:
                    # Map field names from scraper to model fields
                    mapped_data = map_scraped_card_to_model(card_data)

                    if mapped_data is None:
                        continue

                    # Add source information
                    mapped_data['source'] = source
                    mapped_data['source_url'] = source_url
                    mapped_data['import_date'] = import_date
                    
                    # Extract reward categories before creating/updating card
                    reward_categories_json = mapped_data.get('reward_categories', '[]')
                    try:
                        reward_categories = json.loads(reward_categories_json) if isinstance(reward_categories_json, str) else reward_categories_json
                    except (json.JSONDecodeError, TypeError):
                        reward_categories = []
                    
                    # Check if card already exists
                    existing_card = safe_query(CreditCard).filter_by(name=mapped_data['name']).first()
                    if existing_card:
                        # Update existing card
                        for key, value in mapped_data.items():
                            if key in ['reward_categories', 'special_offers'] and isinstance(value, list):
                                setattr(existing_card, key, json.dumps(value))
                            else:
                                setattr(existing_card, key, value)
                        card = existing_card
                    else:
                        # Create new card
                        new_card = CreditCard(**mapped_data)
                        db.session.add(new_card)
                        card = new_card
                    
                    # Flush to get the card ID
                    db.session.flush()
                    
                    # Clear existing reward relationships for this card
                    from app.models.category import CreditCardReward
                    CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
                    
                    # Create CreditCardReward relationship records
                    for reward_data in reward_categories:
                        if isinstance(reward_data, dict):
                            category_name = reward_data.get('category', '')
                            percentage = reward_data.get('percentage', reward_data.get('rate', 1.0))
                            limit = reward_data.get('limit')
                            if category_name and percentage:
                                card.add_reward_category(
                                    category_name=category_name,
                                    reward_percent=float(percentage),
                                    is_bonus=(float(percentage) > 1.0),
                                    limit=float(limit) if limit not in (None, "", "null") else None
                                )
            
            flash(f"Successfully imported {len(cards_data)} credit cards from {source}.", "success")
            return redirect(url_for('credit_cards.index'))
        
        except Exception as e:
            db.session.rollback()
            error_message = f"Error importing credit cards: {str(e)}"
            flash(error_message, "danger")
            print(error_message)
    
    # Pass SOURCE_URLS dictionary to the template
    return render_template('credit_cards/import.html', sources=SOURCE_URLS)

@credit_cards.route('/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Add a new credit card."""
    if request.method == 'POST':
        try:
            # Extract basic card details
            data = {
                'name': request.form.get('name'),
                'issuer_id': request.form.get('issuer_id'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'signup_bonus_points': int(request.form.get('signup_bonus_points', 0)),
                'signup_bonus_value': float(request.form.get('signup_bonus_value', 0)),
                'signup_bonus_min_spend': float(request.form.get('signup_bonus_min_spend', 0)),
                'signup_bonus_time_limit': int(request.form.get('signup_bonus_time_limit', 3)),
                'signup_bonus_type': request.form.get('signup_bonus_type', 'points'),
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
                category_limit = request.form.get(f'category_limit_{idx}')
                if category_name and category_percentage:
                    try:
                        reward_categories.append({
                            'category': category_name,
                            'percentage': float(category_percentage),
                            'limit': float(category_limit) if category_limit not in (None, '', 'null') else None
                        })
                    except ValueError:
                        flash(f'Invalid percentage for {category_name}', 'danger')
                        # Get active categories from database for error case
                        from app.models.category import Category
                        categories = Category.get_active_categories()
                        issuers = CardIssuer.all_ordered()
                        return render_template('credit_cards/new.html', 
                                              categories=categories,
                                              issuers=issuers,
                                              form_action=url_for('credit_cards.new'),
                                              categories_data=True)
            
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
                        # Get active categories from database for error case
                        from app.models.category import Category
                        categories = Category.get_active_categories()
                        issuers = CardIssuer.all_ordered()
                        return render_template('credit_cards/new.html', 
                                              categories=categories,
                                              issuers=issuers,
                                              form_action=url_for('credit_cards.new'),
                                              categories_data=True)
            
            data['special_offers'] = json.dumps(special_offers)
            
            # Validate and create credit card
            schema = CreditCardSchema()
            validated_data = schema.load(data)
            
            # Use the safe_commit context manager
            with safe_commit():
                card = CreditCard(**validated_data)
                db.session.add(card)
            
            # Now add the actual reward categories using the CreditCardReward model
            # No need to clear existing rewards for a new card
            
            # Add rewards from the form
            for reward_data in reward_categories:
                category_name = reward_data.get('category')
                percentage = reward_data.get('percentage')
                limit = reward_data.get('limit')
                if category_name and percentage:
                    card.add_reward_category(
                        category_name=category_name,
                        reward_percent=float(percentage),
                        is_bonus=(percentage > 1.0),  # Consider it a bonus if > 1%
                        limit=float(limit) if limit not in (None, '', 'null') else None
                    )
            
            # Commit the reward changes
            with safe_commit():
                pass
            
            flash('Credit card added successfully!', 'success')
            return redirect(url_for('credit_cards.index'))
        except ValidationError as e:
            flash('Validation error: ' + str(e.messages), 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # Get active categories from database
    from app.models.category import Category
    categories = Category.get_active_categories()
    issuers = CardIssuer.all_ordered()
    
    return render_template('credit_cards/new.html', 
                          categories=categories,
                          issuers=issuers,
                          form_action=url_for('credit_cards.new'),
                          categories_data=True)

@credit_cards.route('/<int:id>')
def show(id):
    """Show a single credit card."""
    card = safe_query(CreditCard).get_or_404(id)
    
    # Get reward categories from the new CreditCardReward system
    reward_categories = []
    for reward in card.rewards:
        reward_categories.append({
            'category': reward.category.display_name,
            'percentage': reward.reward_percent,
            'id': reward.category_id,
            'limit': reward.limit
        })
    
    # Parse special offers (still using JSON for now)
    try:
        special_offers = json.loads(card.special_offers)
    except (json.JSONDecodeError, TypeError):
        special_offers = []
    
    class DummyForm(FlaskForm):
        pass
    form = DummyForm()
    return render_template('credit_cards/show.html', 
                          card=card, 
                          reward_categories=reward_categories,
                          special_offers=special_offers,
                          form=form)

@credit_cards.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Edit a credit card."""
    card = safe_query(CreditCard).get_or_404(id)
    
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
                'issuer_id': request.form.get('issuer_id'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'signup_bonus_points': int(request.form.get('signup_bonus_points', 0)),
                'signup_bonus_value': float(request.form.get('signup_bonus_value', 0)),
                'signup_bonus_min_spend': float(request.form.get('signup_bonus_min_spend', 0)),
                'signup_bonus_time_limit': int(request.form.get('signup_bonus_time_limit', 3)),
                'signup_bonus_type': request.form.get('signup_bonus_type', 'points'),
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
                category_limit = request.form.get(f'category_limit_{idx}')
                if category_name and category_percentage:
                    try:
                        reward_categories.append({
                            'category': category_name,
                            'percentage': float(category_percentage),
                            'limit': float(category_limit) if category_limit not in (None, '', 'null') else None
                        })
                    except ValueError:
                        flash(f'Invalid percentage for {category_name}', 'danger')
                        # Get active categories from database for error case
                        from app.models.category import Category
                        categories = Category.get_active_categories()
                        issuers = CardIssuer.all_ordered()
                        return render_template('credit_cards/edit.html', 
                                              card=card,
                                              categories=categories,
                                              issuers=issuers,
                                              reward_categories=reward_categories,
                                              special_offers=special_offers,
                                              form_action=url_for('credit_cards.edit', id=id),
                                              categories_data=True)
            
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
                    try:
                        special_offers.append({
                            'type': offer_type,
                            'amount': float(offer_amount),
                            'frequency': offer_frequency or 'one_time'
                        })
                    except ValueError:
                        flash(f'Invalid amount for {offer_type}', 'danger')
                        return render_template('credit_cards/edit.html', 
                                              card=card,
                                              reward_categories=reward_categories,
                                              special_offers=special_offers,
                                              form_action=url_for('credit_cards.edit', id=id))
            
            data['special_offers'] = json.dumps(special_offers)
            
            # Update card with new data
            for key, value in data.items():
                setattr(card, key, value)
            
            with safe_commit():
                db.session.add(card)
            
            # Now add the actual reward categories using the CreditCardReward model
            # No need to clear existing rewards for a new card
            
            # Add rewards from the form
            for reward_data in reward_categories:
                category_name = reward_data.get('category')
                percentage = reward_data.get('percentage')
                limit = reward_data.get('limit')
                if category_name and percentage:
                    card.add_reward_category(
                        category_name=category_name,
                        reward_percent=float(percentage),
                        is_bonus=(percentage > 1.0),  # Consider it a bonus if > 1%
                        limit=float(limit) if limit not in (None, '', 'null') else None
                    )
            
            # Commit the reward changes
            with safe_commit():
                pass
            
            flash('Credit card updated successfully!', 'success')
            return redirect(url_for('credit_cards.show', id=card.id))
        except ValidationError as e:
            flash('Validation error: ' + str(e.messages), 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # For GET requests or after validation errors
    # Try to get categories for dropdowns
    try:
        from app.models.category import Category
        categories = Category.get_active_categories()
        issuers = CardIssuer.all_ordered()
    except:
        categories = None
        issuers = None

    return render_template('credit_cards/edit.html', 
                          card=card,
                          categories=categories,
                          issuers=issuers,
                          reward_categories=reward_categories,
                          special_offers=special_offers,
                          form_action=url_for('credit_cards.edit', id=id),
                          categories_data=True)

@credit_cards.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Delete a credit card."""
    card = safe_query(CreditCard).get_or_404(id)
    
    try:
        with safe_commit():
            db.session.delete(card)
        flash('Credit card deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting card: {str(e)}', 'danger')
    
    return redirect(url_for('credit_cards.index'))

def get_issuer_by_name(name: str):
    if not name:
        return None
    return CardIssuer.query.filter_by(name=name).first() 
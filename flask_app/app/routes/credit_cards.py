from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user, login_required
from app import db
from app.models.credit_card import CreditCard
from marshmallow import Schema, fields, ValidationError
from app.utils.card_scraper import scrape_credit_cards, SOURCE_URLS
from app.utils.data_utils import map_scraped_card_to_model
from app.utils.compat import safe_query, safe_commit
import json
import glob
import os
from datetime import datetime
from flask_wtf import FlaskForm
from app.models import CreditCard, Category, CreditCardReward, CardIssuer

credit_cards = Blueprint('credit_cards', __name__)

def import_cards_from_json_data(cards_data: list, source_file: str) -> int:
    """Import cards from a list of card data from JSON files."""
    created_count = 0
    updated_count = 0
    
    for card_data in cards_data:
        try:
            # Get or create issuer
            issuer_name = card_data.get('issuer', 'Unknown')
            issuer = CardIssuer.query.filter_by(name=issuer_name).first()
            if not issuer:
                # Create new issuer if it doesn't exist
                issuer = CardIssuer(name=issuer_name)
                db.session.add(issuer)
                db.session.flush()
            
            # Check if card already exists
            existing_card = CreditCard.query.filter_by(
                name=card_data.get('name'),
                issuer_id=issuer.id
            ).first()
            
            # Prepare card data for database
            db_card_data = {
                'name': card_data.get('name'),
                'issuer_id': issuer.id,
                'annual_fee': card_data.get('annual_fee', 0.0),
                'reward_type': card_data.get('reward_type', 'points'),
                'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                'source': card_data.get('source', 'scraped'),
                'source_url': card_data.get('source_url', ''),
                'import_date': datetime.utcnow()
            }
            
            # Create signup bonus JSON structure from imported data
            signup_bonus_data = None
            signup_bonus_points = card_data.get('signup_bonus_points', 0)
            signup_bonus_value = card_data.get('signup_bonus_value', 0.0)
            signup_bonus_min_spend = card_data.get('signup_bonus_min_spend', 0.0)
            signup_bonus_max_months = card_data.get('signup_bonus_max_months', 3)
            reward_type = card_data.get('reward_type', 'points')
            reward_value_multiplier = card_data.get('reward_value_multiplier', 0.01)
            
            if signup_bonus_points > 0 or signup_bonus_value > 0:
                signup_bonus_data = {}
                
                if reward_type == 'cash_back':
                    amount = signup_bonus_value if signup_bonus_value > 0 else signup_bonus_points
                    signup_bonus_data['cash_back'] = float(amount)
                    signup_bonus_data['value'] = float(amount)
                elif reward_type == 'miles':
                    amount = signup_bonus_points if signup_bonus_points > 0 else signup_bonus_value / reward_value_multiplier
                    signup_bonus_data['miles'] = int(amount)
                    signup_bonus_data['value'] = float(amount * reward_value_multiplier)
                elif reward_type == 'hotel':
                    amount = signup_bonus_points if signup_bonus_points > 0 else signup_bonus_value / reward_value_multiplier
                    signup_bonus_data['points'] = int(amount)
                    signup_bonus_data['value'] = float(amount * reward_value_multiplier)
                else:  # 'points' or default
                    amount = signup_bonus_points if signup_bonus_points > 0 else signup_bonus_value / reward_value_multiplier
                    signup_bonus_data['points'] = int(amount)
                    signup_bonus_data['value'] = float(amount * reward_value_multiplier)
                
                signup_bonus_data['min_spend'] = float(signup_bonus_min_spend)
                signup_bonus_data['max_months'] = int(signup_bonus_max_months)
                
                db_card_data['signup_bonus'] = json.dumps(signup_bonus_data)
            
            if existing_card:
                # Update existing card
                for key, value in db_card_data.items():
                    if key != 'import_date':  # Don't update import_date for existing cards
                        setattr(existing_card, key, value)
                card = existing_card
                updated_count += 1
            else:
                # Create new card
                card = CreditCard(**db_card_data)
                db.session.add(card)
                created_count += 1
            
            db.session.flush()  # Get the card ID
            
            # Clear existing reward relationships for this card
            CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
            
            # Create CreditCardReward relationship records
            reward_categories = card_data.get('reward_categories', [])
            for reward_data in reward_categories:
                category_name = reward_data.get('category')
                rate = reward_data.get('rate', 1.0)
                limit = reward_data.get('limit')
                
                # Map category name to database category
                category = Category.get_by_name(category_name)
                if category:
                    credit_card_reward = CreditCardReward(
                        credit_card_id=card.id,
                        category_id=category.id,
                        reward_percent=float(rate),
                        is_bonus_category=(float(rate) > 1.0),
                        limit=float(limit) if limit not in (None, '', 'null') else None
                    )
                    db.session.add(credit_card_reward)
                else:
                    print(f"     ⚠️  Category '{category_name}' not found for card '{card.name}'")
            
        except Exception as e:
            print(f"     ❌ Error importing card '{card_data.get('name', 'Unknown')}': {e}")
            continue
    
    db.session.commit()
    return created_count + updated_count

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
    special_offers = fields.Str(dump_default='[]')
    signup_bonus_points = fields.Int(dump_default=0)
    signup_bonus_value = fields.Float(dump_default=0.0)
    signup_bonus_min_spend = fields.Float(dump_default=0.0)
    signup_bonus_max_months = fields.Int(dump_default=3)
    reward_type = fields.Str(dump_default='points')
    reward_value_multiplier = fields.Float(dump_default=0.01)

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
    """Import credit cards from a data source or scraped files"""
    if request.method == 'POST':
        import_type = request.form.get('import_type', 'scrape')
        
        if import_type == 'file':
            # Import from selected files
            selected_files = request.form.getlist('selected_files')
            import_all = request.form.get('import_all') == 'on'
            
            try:
                # Get available files
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                output_dir = os.path.join(base_dir, 'data', 'output')
                
                if import_all:
                    # Import all files
                    json_files = sorted(glob.glob(os.path.join(output_dir, '*.json')))
                else:
                    # Import selected files
                    json_files = [os.path.join(output_dir, f) for f in selected_files if f]
                
                total_imported = 0
                
                for json_file in json_files:
                    if not os.path.exists(json_file):
                        continue
                        
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    cards_data = data.get('cards', [])
                    imported_count = import_cards_from_json_data(cards_data, os.path.basename(json_file))
                    total_imported += imported_count
                
                flash(f"Successfully imported {total_imported} credit cards from {len(json_files)} file(s).", "success")
                return redirect(url_for('credit_cards.index'))
                
            except Exception as e:
                db.session.rollback()
                error_message = f"Error importing from files: {str(e)}"
                flash(error_message, "danger")
                print(error_message)
        
        else:
            # Original scraping functionality
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
                        reward_categories = mapped_data.get('reward_categories', [])
                        
                        # Remove reward_categories from mapped_data as it's handled separately
                        mapped_data.pop('reward_categories', None)
                        
                        # Check if card already exists
                        existing_card = safe_query(CreditCard).filter_by(name=mapped_data['name']).first()
                        if existing_card:
                            # Update existing card
                            for key, value in mapped_data.items():
                                if key in ['special_offers'] and isinstance(value, list):
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
                                rate = reward_data.get('rate', 1.0)
                                limit = reward_data.get('limit')
                                if category_name and rate:
                                    card.add_reward_category(
                                        category_name=category_name,
                                        reward_percent=float(rate),
                                        is_bonus=(float(rate) > 1.0),
                                        limit=float(limit) if limit not in (None, "", "null") else None
                                    )
                
                flash(f"Successfully imported {len(cards_data)} credit cards from {source}.", "success")
                return redirect(url_for('credit_cards.index'))
            
            except Exception as e:
                db.session.rollback()
                error_message = f"Error importing credit cards: {str(e)}"
                flash(error_message, "danger")
                print(error_message)
    
    # Get available scraped files for the template
    import glob
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_dir = os.path.join(base_dir, 'data', 'output')
    available_files = []
    
    if os.path.exists(output_dir):
        json_files = sorted(glob.glob(os.path.join(output_dir, '*.json')), reverse=True)  # Newest first
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                file_info = {
                    'filename': os.path.basename(json_file),
                    'full_path': json_file,
                    'size': os.path.getsize(json_file),
                    'modified': datetime.fromtimestamp(os.path.getmtime(json_file)),
                    'card_count': len(data.get('cards', [])),
                    'extraction_summary': data.get('extraction_summary', {})
                }
                available_files.append(file_info)
            except Exception as e:
                print(f"Error reading file {json_file}: {e}")
                continue
    
    # Pass SOURCE_URLS dictionary and available files to the template
    return render_template('credit_cards/import.html', sources=SOURCE_URLS, available_files=available_files)

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
                'reward_type': request.form.get('reward_type', 'points'),
                'reward_value_multiplier': float(request.form.get('reward_value_multiplier', 0.01)),
            }
            
            # Extract signup bonus data separately
            signup_bonus_points = int(request.form.get('signup_bonus_points', 0))
            signup_bonus_min_spend = float(request.form.get('signup_bonus_min_spend', 0))
            signup_bonus_max_months = int(request.form.get('signup_bonus_max_months', 3))
            
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
                            'rate': float(category_percentage),
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
                # Set up signup bonus using the new JSON structure
                if signup_bonus_points > 0:
                    card.update_signup_bonus(signup_bonus_points, signup_bonus_min_spend, signup_bonus_max_months)
                db.session.add(card)
            
            # Now add the actual reward categories using the CreditCardReward model
            # No need to clear existing rewards for a new card
            
            # Add rewards from the form
            for reward_data in reward_categories:
                category_name = reward_data.get('category')
                rate = reward_data.get('rate')
                limit = reward_data.get('limit')
                if category_name and rate:
                    card.add_reward_category(
                        category_name=category_name,
                        reward_percent=float(rate),
                        is_bonus=(rate > 1.0),  # Consider it a bonus if > 1%
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
            'rate': reward.reward_percent,
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
    
    # Get reward categories from the CreditCardReward relationship for form display
    reward_categories = []
    for reward in card.rewards:
        reward_categories.append({
            'category': reward.category.name,  # Use name for form (not display_name)
            'rate': reward.reward_percent,
            'limit': reward.limit
        })
    
    # Parse special offers from JSON
    try:
        special_offers = json.loads(card.special_offers)
    except (json.JSONDecodeError, TypeError):
        special_offers = []
    
    if request.method == 'POST':
        try:
            # Similar processing as in the 'new' route
            data = {
                'name': request.form.get('name'),
                'issuer_id': request.form.get('issuer_id'),
                'annual_fee': float(request.form.get('annual_fee', 0)),
                'reward_type': request.form.get('reward_type', 'points'),
                'reward_value_multiplier': float(request.form.get('reward_value_multiplier', 0.01)),
            }
            
            # Extract signup bonus data separately
            signup_bonus_points = int(request.form.get('signup_bonus_points', 0))
            signup_bonus_min_spend = float(request.form.get('signup_bonus_min_spend', 0))
            signup_bonus_max_months = int(request.form.get('signup_bonus_max_months', 3))
            
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
                            'rate': float(category_percentage),
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
            
            # Update signup bonus using the new JSON structure
            card.update_signup_bonus(signup_bonus_points, signup_bonus_min_spend, signup_bonus_max_months)
            
            with safe_commit():
                db.session.add(card)
            
            # Clear existing reward relationships for this card before adding new ones
            CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
            
            # Add rewards from the form
            for reward_data in reward_categories:
                category_name = reward_data.get('category')
                rate = reward_data.get('rate')
                limit = reward_data.get('limit')
                if category_name and rate:
                    card.add_reward_category(
                        category_name=category_name,
                        reward_percent=float(rate),
                        is_bonus=(rate > 1.0),  # Consider it a bonus if > 1%
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

@credit_cards.route('/export')
@admin_required
def export_cards():
    """Export all credit cards to JSON file with timestamp."""
    try:
        # Get all credit cards with their relationships
        cards = safe_query(CreditCard).all()
        
        # Build export data
        export_data = {
            'export_info': {
                'timestamp': datetime.utcnow().isoformat(),
                'total_cards': len(cards),
                'exported_by': current_user.email if current_user.email else 'anonymous'
            },
            'cards': []
        }
        
        for card in cards:
            # Get reward categories for this card
            reward_categories = []
            for reward in card.rewards:
                reward_categories.append({
                    'category': reward.category.name,
                    'rate': reward.reward_percent,
                    'limit': reward.limit
                })
            
            # Parse special offers from JSON
            try:
                special_offers = json.loads(card.special_offers) if card.special_offers else []
            except (json.JSONDecodeError, TypeError):
                special_offers = []
            
            card_data = {
                'name': card.name,
                'issuer': card.issuer_obj.name,
                'annual_fee': card.annual_fee,
                'reward_type': card.reward_type,
                'reward_value_multiplier': card.reward_value_multiplier,
                'signup_bonus_points': card.signup_bonus_points,
                'signup_bonus_value': card.signup_bonus_value,
                'signup_bonus_min_spend': card.signup_bonus_min_spend,
                'signup_bonus_max_months': card.signup_bonus_max_months,
                'reward_categories': reward_categories,
                'special_offers': special_offers,
                'source': card.source,
                'source_url': card.source_url,
                'import_date': card.import_date.isoformat() if card.import_date else None
            }
            export_data['cards'].append(card_data)
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        filename = f"{timestamp}_exported_cards.json"
        
        # Ensure data/output directory exists
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'data', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Write export file
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        flash(f"Successfully exported {len(cards)} credit cards to {filename}", "success")
        return redirect(url_for('credit_cards.index'))
        
    except Exception as e:
        flash(f"Error exporting credit cards: {str(e)}", "danger")
        return redirect(url_for('credit_cards.index'))


def get_issuer_by_name(name: str):
    if not name:
        return None
    return CardIssuer.query.filter_by(name=name).first() 
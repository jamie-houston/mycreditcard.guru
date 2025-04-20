from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.models.credit_card import CreditCard
from app import db
from app.utils.card_scraper import scrape_credit_cards
from app.utils.data_utils import map_scraped_card_to_model

card_bp = Blueprint('cards', __name__)

@card_bp.route('/import', methods=['GET', 'POST'])
def import_cards():
    """Import credit cards from various sources."""
    if request.method == 'POST':
        source = request.form.get('source', 'nerdwallet')
        try:
            # Scrape cards from source
            scraped_cards = scrape_credit_cards(source)
            
            # Import each card, mapping field names as needed
            for card_data in scraped_cards:
                # Map the field names to match our model
                mapped_data = map_scraped_card_to_model(card_data)
                
                # Check if card already exists to avoid duplicates
                existing_card = CreditCard.query.filter_by(name=mapped_data['name']).first()
                if existing_card:
                    # Update existing card
                    for key, value in mapped_data.items():
                        setattr(existing_card, key, value)
                else:
                    # Create new card
                    new_card = CreditCard(**mapped_data)
                    db.session.add(new_card)
            
            db.session.commit()
            flash(f'Successfully imported cards from {source}', 'success')
            return redirect(url_for('cards.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing cards: {str(e)}', 'danger')
    
    return render_template('cards/import.html') 
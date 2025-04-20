#!/usr/bin/env python
"""
Test script to verify credit card import functionality with source information.
"""

import sys
import json
from datetime import datetime
from app import create_app, db
from app.models.credit_card import CreditCard
from app.utils.card_scraper import scrape_credit_cards
from app.utils.data_utils import map_scraped_card_to_model

def main():
    """Test importing cards with source information."""
    app = create_app('default')
    with app.app_context():
        # Test both sources
        sources = ['sample', 'nerdwallet', 'creditcards.com']
        
        for source in sources:
            print(f"\nTesting import from {source}...")
            
            # Get cards from the source
            cards_data = scrape_credit_cards(source)
            print(f"Found {len(cards_data)} cards from {source}")
            
            if not cards_data:
                print(f"No cards found from {source}")
                continue
            
            # Source URLs for attribution
            source_urls = {
                'nerdwallet': 'https://www.nerdwallet.com/the-best-credit-cards',
                'creditcards.com': 'https://www.creditcards.com/best-credit-cards/',
                'sample': 'Sample Data'
            }
            source_url = source_urls.get(source, '')
            import_date = datetime.utcnow()
            
            # Process the first card only for the test
            card_data = cards_data[0]
            print(f"Processing card: {card_data['name']}")
            
            # Map the fields
            mapped_data = map_scraped_card_to_model(card_data)
            
            # Add source information
            mapped_data['source'] = source
            mapped_data['source_url'] = source_url
            mapped_data['import_date'] = import_date
            
            # Check if card exists
            existing_card = CreditCard.query.filter_by(name=mapped_data['name']).first()
            if existing_card:
                print(f"Card already exists: {existing_card.name}")
                
                # Update with new source info
                existing_card.source = source
                existing_card.source_url = source_url
                existing_card.import_date = import_date
                db.session.commit()
                
                print(f"Updated source info for {existing_card.name}:")
                print(f"  Source: {existing_card.source}")
                print(f"  Source URL: {existing_card.source_url}")
                print(f"  Import Date: {existing_card.import_date}")
            else:
                # Create a new card
                new_card = CreditCard(**mapped_data)
                db.session.add(new_card)
                db.session.commit()
                
                print(f"Added new card: {new_card.name}")
                print(f"  Source: {new_card.source}")
                print(f"  Source URL: {new_card.source_url}")
                print(f"  Import Date: {new_card.import_date}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
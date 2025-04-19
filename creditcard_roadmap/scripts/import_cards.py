#!/usr/bin/env python
"""Script to import credit cards from NerdWallet."""

import os
import sys
import json
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.utils.card_scraper import scrape_credit_cards

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('import_cards')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Import credit cards from NerdWallet')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation for scraping')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of cards to import (0 for no limit)')
    parser.add_argument('--clear', action='store_true', help='Clear existing cards before import')
    return parser.parse_args()

def import_cards(use_proxies: bool = False, limit: int = 0, clear: bool = False):
    """Import credit cards from NerdWallet."""
    logger.info("Starting card import script")
    
    # Create app context
    app = create_app('default')
    with app.app_context():
        # Clear existing cards if requested
        if clear:
            try:
                num_deleted = CreditCard.query.delete()
                db.session.commit()
                logger.info(f"Cleared {num_deleted} existing credit cards")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error clearing existing cards: {e}")
                return
        
        # Scrape credit cards data directly from the main table
        cards_data = scrape_credit_cards(use_proxies)
        
        if not cards_data:
            logger.warning("No credit cards found to import")
            return
        
        if limit > 0 and len(cards_data) > limit:
            logger.info(f"Limiting to {limit} cards (out of {len(cards_data)} scraped)")
            cards_data = cards_data[:limit]
        
        # Import each card to database
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        for card_data in cards_data:
            try:
                # Skip cards without a name
                if not card_data.get('name'):
                    logger.warning(f"Skipping card with missing name: {card_data}")
                    skipped_count += 1
                    continue
                
                # Remove fields that aren't in the model
                if 'rewards_rate' in card_data:
                    # Store this somewhere if needed for logging
                    rewards_rate = card_data.pop('rewards_rate')
                    logger.info(f"Removed rewards_rate '{rewards_rate}' from card data")
                
                # Filter out any other fields that don't match the model
                valid_fields = ['name', 'issuer', 'annual_fee', 'reward_categories', 'offers', 
                               'signup_bonus_points', 'signup_bonus_value', 'signup_bonus_spend_requirement',
                               'signup_bonus_time_period', 'is_active']
                
                filtered_card_data = {k: v for k, v in card_data.items() if k in valid_fields}
                
                # Convert list/dict fields to JSON strings
                if 'reward_categories' in filtered_card_data:
                    filtered_card_data['reward_categories'] = json.dumps(filtered_card_data['reward_categories'])
                if 'offers' in filtered_card_data:
                    filtered_card_data['offers'] = json.dumps(filtered_card_data['offers'])
                
                # Check if card already exists by name and issuer
                existing_card = CreditCard.query.filter_by(
                    name=filtered_card_data['name'],
                    issuer=filtered_card_data['issuer']
                ).first()
                
                if existing_card:
                    # Update existing card
                    for key, value in filtered_card_data.items():
                        setattr(existing_card, key, value)
                    updated_count += 1
                    logger.info(f"Updated card: {filtered_card_data['name']}")
                else:
                    # Create new card
                    card = CreditCard(**filtered_card_data)
                    db.session.add(card)
                    imported_count += 1
                    logger.info(f"Added new card: {filtered_card_data['name']}")
                
                # Commit every 10 cards to avoid large transactions
                if (imported_count + updated_count) % 10 == 0:
                    db.session.commit()
                    logger.info(f"Committed batch of cards (progress: {imported_count + updated_count}/{len(cards_data)})")
                
            except Exception as e:
                logger.error(f"Error importing card {card_data.get('name', 'unknown')}: {e}")
                logger.exception(e)
                skipped_count += 1
        
        # Final commit for any remaining cards
        try:
            db.session.commit()
            logger.info(f"Import completed. Added {imported_count} new cards, updated {updated_count} existing cards, skipped {skipped_count} cards.")
            return imported_count, updated_count, skipped_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during final commit: {e}")
            return None

if __name__ == "__main__":
    args = parse_arguments()
    import_cards(args.use_proxies, args.limit, args.clear) 
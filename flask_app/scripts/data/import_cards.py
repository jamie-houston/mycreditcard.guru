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
from app.models.category import Category, CreditCardReward
from app.models import CardIssuer
from app.utils.card_scraper import scrape_credit_cards
from app.utils.data_utils import map_scraped_card_to_model

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('import_cards')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Import credit cards from NerdWallet')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation for scraping')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of cards to import (0 for no limit)')
    parser.add_argument('--clear', action='store_true', help='Clear existing cards before import')
    parser.add_argument('--json', type=str, help='Import cards from a JSON file instead of scraping')
    return parser.parse_args()

def validate_and_process_reward_categories(reward_categories_data, card_name):
    """
    Validate and process reward categories using the Category model's aliases system.
    
    Args:
        reward_categories_data: List of reward category dictionaries
        card_name: Name of the card (for logging)
        
    Returns:
        List of valid reward category dictionaries with mapped category names
    """
    if not reward_categories_data:
        return []
    
    valid_rewards = []
    unmapped_categories = []
    
    for reward_data in reward_categories_data:
        if not isinstance(reward_data, dict):
            logger.warning(f"Card '{card_name}': Invalid reward data format: {reward_data}")
            continue
        
        # Get category name and rate
        category_name = reward_data.get('category', '').strip()
        rate = reward_data.get('rate', reward_data.get('percentage', 1.0))
        
        if not category_name:
            logger.warning(f"Card '{card_name}': Empty category name in reward data: {reward_data}")
            continue
        
        # Try to find category using aliases system
        category = Category.get_by_name_or_alias(category_name)
        
        if category:
            logger.info(f"Card '{card_name}': Mapped '{category_name}' -> '{category.name}' ({rate}%)")
            valid_rewards.append({
                'category_id': category.id,
                'category_name': category.name,
                'reward_percent': float(rate),
                'is_bonus': float(rate) > 1.0
            })
        else:
            logger.warning(f"Card '{card_name}': No category found for '{category_name}' (rate: {rate}%)")
            unmapped_categories.append(category_name)
    
    if unmapped_categories:
        logger.warning(f"Card '{card_name}': Unmapped categories: {unmapped_categories}")
        logger.info("Available categories and their aliases:")
        categories = Category.get_active_categories()
        for cat in categories:
            aliases = cat.get_aliases()
            aliases_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
            logger.info(f"  - {cat.name}: {cat.display_name}{aliases_str}")
    
    return valid_rewards

def create_card_rewards(card, valid_rewards):
    """Create CreditCardReward entries for valid categories."""
    for reward_data in valid_rewards:
        # Check if reward already exists
        existing_reward = CreditCardReward.query.filter_by(
            credit_card_id=card.id,
            category_id=reward_data['category_id']
        ).first()
        
        if existing_reward:
            existing_reward.reward_percent = reward_data['reward_percent']
            existing_reward.is_bonus_category = reward_data['is_bonus']
        else:
            new_reward = CreditCardReward(
                credit_card_id=card.id,
                category_id=reward_data['category_id'],
                reward_percent=reward_data['reward_percent'],
                is_bonus_category=reward_data['is_bonus']
            )
            db.session.add(new_reward)

def import_cards_from_json(json_file):
    """Import credit cards from a JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle new structure with valid_cards and problematic_cards
        if isinstance(data, dict):
            if 'valid_cards' in data and 'problematic_cards' in data:
                valid_cards = data.get('valid_cards', [])
                problematic_cards = data.get('problematic_cards', [])
                extraction_summary = data.get('extraction_summary', {})
                
                logger.info(f"📊 New categorized JSON structure detected:")
                logger.info(f"  ✅ Valid cards (ready for import): {len(valid_cards)}")
                logger.info(f"  ⚠️  Problematic cards (skipped): {len(problematic_cards)}")
                
                # Show extraction summary if available
                if extraction_summary:
                    logger.info(f"  📄 Source file: {extraction_summary.get('source_file', 'Unknown')}")
                    logger.info(f"  🕒 Extracted: {extraction_summary.get('extraction_timestamp', 'Unknown')}")
                    if 'available_issuers' in extraction_summary:
                        issuers = extraction_summary['available_issuers']
                        logger.info(f"  🏦 Available issuers: {', '.join(issuers)}")
                
                # Show detailed issue breakdown
                if problematic_cards:
                    logger.info(f"📋 Problematic cards will be skipped:")
                    issue_counts = {}
                    for card in problematic_cards:
                        for issue in card.get('issues', []):
                            issue_counts[issue] = issue_counts.get(issue, 0) + 1
                    for issue, count in issue_counts.items():
                        logger.info(f"    • {issue.replace('_', ' ').title()}: {count} cards")
                    
                    # Show a few examples
                    logger.info(f"  📝 Example problematic cards:")
                    for i, card in enumerate(problematic_cards[:3]):
                        issues = ', '.join(card.get('issues', []))
                        logger.info(f"    {i+1}. {card.get('name', 'Unknown')}: {issues}")
                    if len(problematic_cards) > 3:
                        logger.info(f"    ... and {len(problematic_cards) - 3} more")
                
                logger.info(f"🎯 Proceeding with import of {len(valid_cards)} valid cards only")
                return valid_cards  # Only return valid cards for import
            elif 'cards' in data:
                # Old structure
                cards_data = data['cards']
                logger.info(f"Old JSON structure detected: {len(cards_data)} cards")
                return cards_data
            else:
                # Assume it's a single card
                logger.info(f"Single card structure detected")
                return [data]
        elif isinstance(data, list):
            # Direct array of cards
            logger.info(f"Direct array structure detected: {len(data)} cards")
            return data
        else:
            logger.error(f"Unexpected JSON structure in {json_file}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading cards from JSON file: {e}")
        return []

def get_issuer_by_name(name: str):
    if not name:
        return None
    return CardIssuer.query.filter_by(name=name).first()

def import_cards(use_proxies: bool = False, limit: int = 0, clear: bool = False, json_file: str = None):
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
        
        # Get card data from JSON file or by scraping
        if json_file:
            cards_data = import_cards_from_json(json_file)
        else:
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
        failed_cards = []  # Track failed cards with reasons
        
        for card_data in cards_data:
            try:
                # Skip cards without a name
                if not card_data.get('name'):
                    reason = f"Missing name: {card_data}"
                    logger.warning(f"Skipping card with missing name: {card_data}")
                    skipped_count += 1
                    failed_cards.append({'card': card_data, 'reason': reason})
                    continue
                
                card_name = card_data['name']
                
                # Normalize reward_categories if it's a dict (convert to list of dicts)
                reward_categories_data = card_data.get('reward_categories')
                if isinstance(reward_categories_data, dict):
                    normalized_list = []
                    for k, v in reward_categories_data.items():
                        normalized_list.append({'category': k, 'rate': v})
                    reward_categories_data = normalized_list
                
                # Process and validate reward categories
                valid_rewards = validate_and_process_reward_categories(reward_categories_data, card_name)
                
                # Remove fields that aren't in the model or are processed separately
                fields_to_remove = ['rewards_rate', 'reward_categories']
                for field in fields_to_remove:
                    if field in card_data:
                        card_data.pop(field)
                
                # Define allowed fields for CreditCard model
                allowed_fields = ['name', 'issuer_id', 'annual_fee', 'signup_bonus_points', 'signup_bonus_value', 
                                 'signup_bonus_min_spend', 'signup_bonus_max_months', 'signup_bonus_type', 
                                 'point_value', 'reward_categories', 'special_offers', 'description', 'website_url',
                                 'is_active', 'source', 'source_url']
                
                # Field mapping from scraped data to model fields
                field_mapping = {
                    'signup_bonus_spend_requirement': 'signup_bonus_min_spend',
                    'signup_bonus_time_period': 'signup_bonus_max_months',
                    'offers': 'special_offers'
                }
                
                # Rename fields to match model
                for scraper_field, model_field in field_mapping.items():
                    if scraper_field in card_data and model_field in allowed_fields:
                        card_data[model_field] = card_data.pop(scraper_field)
                
                # Now filter the fields
                filtered_card_data = {k: v for k, v in card_data.items() if k in allowed_fields}
                
                # Use map_scraped_card_to_model to handle issuer mapping and validation
                mapped_card_data = map_scraped_card_to_model(filtered_card_data)
                if mapped_card_data is None:
                    reason = "Missing or invalid issuer."
                    print(f"Skipping card '{filtered_card_data['name']}' - {reason}")
                    failed_cards.append({'card': filtered_card_data, 'reason': reason})
                    continue
                filtered_card_data = mapped_card_data
                
                # Add empty reward_categories for backward compatibility
                filtered_card_data['reward_categories'] = json.dumps([])
                
                # Convert list/dict fields to JSON strings
                if 'special_offers' in filtered_card_data:
                    filtered_card_data['special_offers'] = json.dumps(filtered_card_data['special_offers'])
                
                # Check if card already exists by name and issuer_id
                card = CreditCard.query.filter_by(name=filtered_card_data['name'], issuer_id=filtered_card_data['issuer_id']).first()
                if card:
                    # Update existing card - will overwrite all fields
                    for key, value in filtered_card_data.items():
                        setattr(card, key, value)
                    
                    # Clear existing rewards and add new ones
                    CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
                    create_card_rewards(card, valid_rewards)
                    
                    updated_count += 1
                    logger.info(f"Updated card: {filtered_card_data['name']} (with {len(valid_rewards)} reward categories)")
                else:
                    # Create new card
                    card = CreditCard(
                        **{k: v for k, v in filtered_card_data.items() if k != 'reward_categories'}
                    )
                    db.session.add(card)
                    db.session.flush()  # Get the card ID
                    
                    # Add reward categories
                    create_card_rewards(card, valid_rewards)
                    # Debug: Log how many rewards were created for this card
                    reward_count = CreditCardReward.query.filter_by(credit_card_id=card.id).count()
                    logger.info(f"Card '{filtered_card_data['name']}' now has {reward_count} rewards after import.")
                    
                    imported_count += 1
                    logger.info(f"Added new card: {filtered_card_data['name']} (with {len(valid_rewards)} reward categories)")
                
                # Commit every 10 cards to avoid large transactions
                if (imported_count + updated_count) % 10 == 0:
                    db.session.commit()
                    logger.info(f"Committed batch of cards (progress: {imported_count + updated_count}/{len(cards_data)})")
                
            except Exception as e:
                reason = f"Exception: {e}"
                logger.error(f"Error importing card {card_data.get('name', 'unknown')}: {e}")
                logger.exception(e)
                skipped_count += 1
                failed_cards.append({'card': card_data, 'reason': reason})
        
        # Final commit for any remaining cards
        try:
            db.session.commit()
            logger.info(f"Import completed. Added {imported_count} new cards, updated {updated_count} existing cards, skipped {skipped_count} cards.")
            if failed_cards:
                print("\n--- Failed Card Imports ---")
                for fail in failed_cards:
                    name = fail['card'].get('name', '[unknown]')
                    reason = fail['reason']
                    print(f"- '{name}': {reason}")
                print(f"\nTotal failed cards: {len(failed_cards)}. That's more than the number of British sunny days in a year!")
            else:
                print("\nAll cards imported successfully. Not a single one left behind—unlike my umbrella on the train.")
            return imported_count, updated_count, skipped_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during final commit: {e}")
            return None

def print_all_categories():
    app = create_app('default')
    with app.app_context():
        from app.models.category import Category
        categories = Category.query.all()
        print("\nAll categories in the database:")
        for cat in categories:
            print(f"- {cat.name} (active: {cat.is_active})")

if __name__ == "__main__":
    args = parse_arguments()
    import_cards(args.use_proxies, args.limit, args.clear, args.json) 
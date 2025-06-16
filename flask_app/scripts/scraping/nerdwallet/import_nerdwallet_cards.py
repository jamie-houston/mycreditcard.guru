#!/usr/bin/env python3
"""
Script to import scraped NerdWallet credit card data into the database.
This script cleans and formats the scraped data to match the database schema.
"""

import os
import sys
import json
import re
from typing import List, Dict, Optional
import logging

# Add the flask_app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clean_card_name(name: str) -> str:
    """Clean and standardize card names."""
    if not name:
        return ""
    
    # Remove common prefixes that aren't part of the actual card name
    prefixes_to_remove = [
        "Our pick for:",
        "Best for:",
        "Top pick:",
        "Editor's choice:",
        "Featured:",
    ]
    
    cleaned = name
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Skip generic/non-card names
    skip_patterns = [
        r'^Find the right credit card',
        r'^Whether you want to pay',
        r'^Compare credit cards',
        r'^Get started',
        r'^Apply now',
        r'^\w+\s+(cash back|miles|points)$',  # Generic category names
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return ""
    
    return cleaned


def parse_annual_fee(fee_str: str) -> float:
    """Parse annual fee string to float."""
    if not fee_str:
        return 0.0
    
    # Handle "no annual fee" cases
    if re.search(r'no\s+annual\s+fee', fee_str, re.IGNORECASE):
        return 0.0
    
    # Extract numeric value
    match = re.search(r'\$?(\d{1,3}(?:,\d{3})*)', fee_str)
    if match:
        return float(match.group(1).replace(',', ''))
    
    return 0.0


def parse_bonus_offer(bonus_str: str) -> Dict[str, any]:
    """Parse bonus offer string to extract points/value."""
    if not bonus_str:
        return {'points': 0, 'value': 0.0}
    
    # Remove currency symbols and commas
    cleaned = bonus_str.replace('$', '').replace(',', '')
    
    # Try to extract numeric value
    match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
    if match:
        amount = float(match.group(1))
        
        # Determine if it's cash or points/miles
        if '$' in bonus_str or 'cash' in bonus_str.lower():
            return {'points': 0, 'value': amount}
        else:
            # Assume points/miles - estimate value at 1 cent per point
            return {'points': int(amount), 'value': amount * 0.01}
    
    return {'points': 0, 'value': 0.0}


def parse_spending_requirement(spend_str: str) -> float:
    """Parse spending requirement string to float."""
    if not spend_str:
        return 0.0
    
    # Extract numeric value
    match = re.search(r'\$?(\d{1,3}(?:,\d{3})*)', spend_str)
    if match:
        return float(match.group(1).replace(',', ''))
    
    return 0.0


def normalize_issuer_name(issuer_str: str) -> str:
    """Normalize issuer names to match database standards."""
    if not issuer_str:
        return ""
    
    # Common issuer name mappings
    issuer_mappings = {
        'american express': 'American Express',
        'amex': 'American Express',
        'chase': 'Chase',
        'capital one': 'Capital One',
        'citi': 'Citi',
        'citibank': 'Citi',
        'discover': 'Discover',
        'bank of america': 'Bank of America',
        'wells fargo': 'Wells Fargo',
        'us bank': 'US Bank',
        'barclays': 'Barclays',
    }
    
    normalized = issuer_str.lower().strip()
    return issuer_mappings.get(normalized, issuer_str.title())


def determine_reward_type(card_name: str, raw_text: str) -> str:
    """Determine the reward type based on card name and description."""
    combined_text = f"{card_name} {raw_text}".lower()
    
    if any(keyword in combined_text for keyword in ['cash back', 'cashback', 'cash rewards']):
        return 'cash_back'
    elif any(keyword in combined_text for keyword in ['miles', 'airline', 'delta', 'united', 'american airlines', 'southwest']):
        return 'miles'
    elif any(keyword in combined_text for keyword in ['hotel', 'marriott', 'hilton', 'hyatt', 'ihg']):
        return 'hotel'
    else:
        return 'points'  # Default


def get_or_create_issuer(issuer_name: str) -> CardIssuer:
    """Get existing issuer or create new one."""
    if not issuer_name:
        # Create a default "Unknown" issuer
        issuer_name = "Unknown"
    
    issuer = CardIssuer.query.filter_by(name=issuer_name).first()
    if not issuer:
        issuer = CardIssuer(name=issuer_name)
        db.session.add(issuer)
        db.session.flush()  # Get the ID
        logger.info(f"Created new issuer: {issuer_name}")
    
    return issuer


def clean_and_format_card_data(raw_cards: List[Dict]) -> List[Dict]:
    """Clean and format raw scraped card data for database import."""
    cleaned_cards = []
    seen_cards = set()  # To avoid duplicates
    
    for raw_card in raw_cards:
        try:
            # Clean card name
            card_name = clean_card_name(raw_card.get('name', ''))
            if not card_name or len(card_name) < 5:
                continue
            
            # Skip duplicates (same name)
            if card_name in seen_cards:
                continue
            seen_cards.add(card_name)
            
            # Parse and clean other fields
            annual_fee = parse_annual_fee(raw_card.get('annual_fee', ''))
            bonus_data = parse_bonus_offer(raw_card.get('bonus_offer', ''))
            spending_req = parse_spending_requirement(raw_card.get('spending_requirement', ''))
            issuer_name = normalize_issuer_name(raw_card.get('issuer', ''))
            reward_type = determine_reward_type(card_name, raw_card.get('raw_text_sample', ''))
            
            # Determine reward value multiplier based on type
            reward_multipliers = {
                'cash_back': 0.01,  # 1 cent per point
                'points': 0.01,     # 1 cent per point (conservative)
                'miles': 0.015,     # 1.5 cents per mile (average)
                'hotel': 0.005,     # 0.5 cents per point (conservative)
            }
            
            cleaned_card = {
                'name': card_name,
                'issuer_name': issuer_name,
                'annual_fee': annual_fee,
                'reward_type': reward_type,
                'reward_value_multiplier': reward_multipliers.get(reward_type, 0.01),
                'signup_bonus_points': bonus_data['points'],
                'signup_bonus_value': bonus_data['value'],
                'signup_bonus_min_spend': spending_req,
                'signup_bonus_max_months': 3,  # Default assumption
                'source': 'nerdwallet',
                'source_url': 'https://www.nerdwallet.com/best/credit-cards/bonus-offers',
                'raw_data': raw_card  # Keep original for reference
            }
            
            cleaned_cards.append(cleaned_card)
            
        except Exception as e:
            logger.warning(f"Error processing card {raw_card.get('name', 'Unknown')}: {e}")
            continue
    
    return cleaned_cards


def import_cards_to_database(cleaned_cards: List[Dict], dry_run: bool = True) -> Dict:
    """Import cleaned card data to the database."""
    stats = {
        'processed': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for card_data in cleaned_cards:
        try:
            stats['processed'] += 1
            
            # Get or create issuer
            issuer = get_or_create_issuer(card_data['issuer_name'])
            
            # Check if card already exists
            existing_card = CreditCard.query.filter_by(
                name=card_data['name'],
                issuer_id=issuer.id
            ).first()
            
            if existing_card:
                # Update existing card
                if not dry_run:
                    existing_card.annual_fee = card_data['annual_fee']
                    existing_card.reward_type = card_data['reward_type']
                    existing_card.reward_value_multiplier = card_data['reward_value_multiplier']
                    existing_card.signup_bonus_points = card_data['signup_bonus_points']
                    existing_card.signup_bonus_value = card_data['signup_bonus_value']
                    existing_card.signup_bonus_min_spend = card_data['signup_bonus_min_spend']
                    existing_card.signup_bonus_max_months = card_data['signup_bonus_max_months']
                    existing_card.source = card_data['source']
                    existing_card.source_url = card_data['source_url']
                
                stats['updated'] += 1
                logger.info(f"{'Would update' if dry_run else 'Updated'} existing card: {card_data['name']}")
            
            else:
                # Create new card
                if not dry_run:
                    new_card = CreditCard(
                        name=card_data['name'],
                        issuer_id=issuer.id,
                        annual_fee=card_data['annual_fee'],
                        reward_type=card_data['reward_type'],
                        reward_value_multiplier=card_data['reward_value_multiplier'],
                        signup_bonus_points=card_data['signup_bonus_points'],
                        signup_bonus_value=card_data['signup_bonus_value'],
                        signup_bonus_min_spend=card_data['signup_bonus_min_spend'],
                        signup_bonus_max_months=card_data['signup_bonus_max_months'],
                        source=card_data['source'],
                        source_url=card_data['source_url'],
                        reward_categories='[]'  # Default empty categories
                    )
                    db.session.add(new_card)
                
                stats['created'] += 1
                logger.info(f"{'Would create' if dry_run else 'Created'} new card: {card_data['name']}")
        
        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Error importing card {card_data.get('name', 'Unknown')}: {e}")
    
    if not dry_run:
        try:
            db.session.commit()
            logger.info("Database changes committed successfully")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing to database: {e}")
            raise
    
    return stats


def main():
    """Main function to import NerdWallet cards."""
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    scraped_file = os.path.join(base_dir, 'data', 'scraped', 'scraped_nerdwallet_cards.json')
    
    if not os.path.exists(scraped_file):
        logger.error(f"Scraped data file not found: {scraped_file}")
        return
    
    # Load scraped data
    logger.info(f"Loading scraped data from: {scraped_file}")
    with open(scraped_file, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)
    
    raw_cards = scraped_data.get('cards', [])
    logger.info(f"Found {len(raw_cards)} raw cards to process")
    
    # Clean and format data
    logger.info("Cleaning and formatting card data...")
    cleaned_cards = clean_and_format_card_data(raw_cards)
    logger.info(f"Cleaned data resulted in {len(cleaned_cards)} valid cards")
    
    # Save cleaned data for review
    output_dir = os.path.join(base_dir, 'data', 'scraped')
    os.makedirs(output_dir, exist_ok=True)
    cleaned_file = os.path.join(output_dir, 'cleaned_nerdwallet_cards.json')
    with open(cleaned_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_cards, f, indent=2, ensure_ascii=False)
    logger.info(f"Cleaned data saved to: {cleaned_file}")
    
    # Create Flask app context for database operations
    app = create_app()
    with app.app_context():
        # First, do a dry run
        logger.info("Performing dry run...")
        dry_run_stats = import_cards_to_database(cleaned_cards, dry_run=True)
        
        print("\n" + "="*60)
        print("DRY RUN RESULTS")
        print("="*60)
        print(f"Cards processed: {dry_run_stats['processed']}")
        print(f"Would create: {dry_run_stats['created']}")
        print(f"Would update: {dry_run_stats['updated']}")
        print(f"Would skip: {dry_run_stats['skipped']}")
        print(f"Errors: {dry_run_stats['errors']}")
        
        # Ask user if they want to proceed with actual import
        if dry_run_stats['errors'] == 0:
            response = input("\nProceed with actual database import? (y/N): ")
            if response.lower() == 'y':
                logger.info("Performing actual database import...")
                actual_stats = import_cards_to_database(cleaned_cards, dry_run=False)
                
                print("\n" + "="*60)
                print("ACTUAL IMPORT RESULTS")
                print("="*60)
                print(f"Cards processed: {actual_stats['processed']}")
                print(f"Created: {actual_stats['created']}")
                print(f"Updated: {actual_stats['updated']}")
                print(f"Skipped: {actual_stats['skipped']}")
                print(f"Errors: {actual_stats['errors']}")
            else:
                print("Import cancelled by user.")
        else:
            print(f"\nDry run had {dry_run_stats['errors']} errors. Please review and fix before importing.")


if __name__ == '__main__':
    main() 
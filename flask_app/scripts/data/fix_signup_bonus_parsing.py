#!/usr/bin/env python
"""Script to fix signup bonus parsing in existing JSON files."""

import os
import sys
import json
import logging
import argparse
import re
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fix_signup_bonus')

def parse_intro_offer_fixed(intro_text: str, intro_display: str = None) -> Dict[str, Any]:
    """Improved parsing of intro offer text to extract bonus details."""
    if not intro_text and not intro_display:
        return {'points': 0, 'value': 0.0, 'spending_requirement': 0.0, 'months': 3}
    
    # Combine intro_text and intro_display for better parsing
    combined_text = f"{intro_text or ''} {intro_display or ''}".strip()
    if not combined_text:
        return {'points': 0, 'value': 0.0, 'spending_requirement': 0.0, 'months': 3}
    
    result = {'points': 0, 'value': 0.0, 'spending_requirement': 0.0, 'months': 3}
    
    # Extract bonus amount - improved patterns
    bonus_patterns = [
        # Specific patterns for points/miles first
        r'earn (\d{1,3}(?:,\d{3})*)\s+(?:bonus\s+)?(?:hilton honors\s+bonus\s+)?(?:miles|points)',
        r'bonus of (\d{1,3}(?:,\d{3})*)\s+(?:miles|points)',
        r'earn (\d{1,3}(?:,\d{3})*)\s+(?:membership rewards|thankyou|aadvantage|skymiles)?\s*(?:bonus\s+)?(?:miles|points)',
        r'(\d{1,3}(?:,\d{3})*)\s+(?:bonus\s+)?(?:hilton honors\s+bonus\s+)?(?:miles|points)',
        # Cash patterns
        r'earn a \$(\d{1,3}(?:,\d{3})*)\s+(?:cash back|bonus|statement credit)',
        r'\$(\d{1,3}(?:,\d{3})*)\s+(?:cash back|bonus|statement credit|online cash rewards bonus)',
        # Pattern to catch just numbers in intro_display
        r'^(\d{1,3}(?:,\d{3})*)$',  # Just a number like "130,000"
        r'^(\d{1,3}(?:,\d{3})*)\s+(?:miles|points)$',  # Number + type like "75,000 miles"
        # Generic patterns
        r'earn (\d{1,3}(?:,\d{3})*)',
        r'bonus of (\d{1,3}(?:,\d{3})*)',
    ]
    
    for pattern in bonus_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            amount = int(match.group(1).replace(',', ''))
            # Check if this is a cash bonus
            if '$' in match.group(0) or 'cash' in match.group(0).lower() or 'statement credit' in match.group(0).lower():
                result['value'] = float(amount)
            else:
                result['points'] = amount
            break
    
    # If we still don't have points, try to extract from intro_display alone
    if result['points'] == 0 and result['value'] == 0.0 and intro_display:
        # Try to extract pure numbers
        number_match = re.search(r'(\d{1,3}(?:,\d{3})*)', intro_display)
        if number_match:
            amount = int(number_match.group(1).replace(',', ''))
            # Check if it's cash
            if '$' in intro_display:
                result['value'] = float(amount)
            else:
                result['points'] = amount
    
    # Extract spending requirement
    spend_patterns = [
        r'spend \$(\d{1,3}(?:,\d{3})*)',
        r'after you spend \$(\d{1,3}(?:,\d{3})*)',
        r'after \$(\d{1,3}(?:,\d{3})*)',
        r'make at least \$(\d{1,3}(?:,\d{3})*)',
        r'make \$(\d{1,3}(?:,\d{3})*)',
    ]
    
    for pattern in spend_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            result['spending_requirement'] = float(match.group(1).replace(',', ''))
            break
    
    # Extract time period - improved patterns
    month_patterns = [
        r'within (\d+) months?',
        r'in the first (\d+) months?',
        r'first (\d+) months?',
        r'in (\d+) months?',
        r'within the first (\d+) months?',
        r'in your first (\d+) months?',
        r'first (\d+) months? from account opening',
        r'within (\d+) months? from account opening',
        r'(\d+) months? of card membership',
        r'first (\d+) months? of account opening',
        r'first (\d+) days' # Handle days and convert to months
    ]
    
    for pattern in month_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            time_value = int(match.group(1))
            if 'days' in pattern:
                # Convert days to months (approximation)
                result['months'] = max(1, round(time_value / 30))
            else:
                result['months'] = time_value
            break
    
    # Extract value if mentioned (e.g., "equal to $750 in travel")
    value_patterns = [
        r'equal to \$(\d{1,3}(?:,\d{3})*)',
        r'worth \$(\d{1,3}(?:,\d{3})*)',
        r'value of \$(\d{1,3}(?:,\d{3})*)',
        r'redeemable for \$(\d{1,3}(?:,\d{3})*)',
        r'that\'s a \$(\d{1,3}(?:,\d{3})*)'
    ]
    
    for pattern in value_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match and result['value'] == 0.0:
            result['value'] = float(match.group(1).replace(',', ''))
            break
    
    return result

def fix_card_signup_bonus(card: Dict[str, Any]) -> bool:
    """Fix signup bonus parsing for a single card."""
    # Check if card needs fixing
    current_points = card.get('signup_bonus_points', 0)
    current_value = card.get('signup_bonus_value', 0.0)
    
    # If both are already set and non-zero, skip
    if current_points > 0 or current_value > 0.0:
        return False
    
    intro_tooltip = card.get('intro_offer_tooltip', '')
    intro_display = card.get('intro_offer_display', '')
    
    # Try to parse with improved function
    parsed = parse_intro_offer_fixed(intro_tooltip, intro_display)
    
    # Update if we found better values
    updated = False
    if parsed['points'] > 0 and current_points == 0:
        card['signup_bonus_points'] = parsed['points']
        updated = True
    
    if parsed['value'] > 0.0 and current_value == 0.0:
        card['signup_bonus_value'] = parsed['value']
        updated = True
    
    if parsed['spending_requirement'] > 0.0 and card.get('signup_bonus_min_spend', 0.0) == 0.0:
        card['signup_bonus_min_spend'] = parsed['spending_requirement']
        updated = True
    
    if parsed['months'] != 3 and card.get('signup_bonus_max_months', 3) == 3:
        card['signup_bonus_max_months'] = parsed['months']
        updated = True
    
    return updated

def fix_json_file(file_path: str, output_path: str = None) -> None:
    """Fix signup bonus parsing in a JSON file."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    logger.info(f"Processing file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different file structures
    cards = []
    if isinstance(data, dict):
        if 'cards' in data:
            cards = data['cards']
        elif 'extraction_summary' in data:
            cards = data.get('cards', [])
        else:
            # Assume it's a dict with card data directly
            cards = [data]
    elif isinstance(data, list):
        cards = data
    
    if not cards:
        logger.warning(f"No cards found in {file_path}")
        return
    
    # Fix each card
    fixed_count = 0
    total_cards = len(cards)
    
    for i, card in enumerate(cards):
        if fix_card_signup_bonus(card):
            fixed_count += 1
            logger.info(f"Fixed signup bonus for: {card.get('name', f'Card {i}')}")
            
            # Log the changes
            points = card.get('signup_bonus_points', 0)
            value = card.get('signup_bonus_value', 0.0)
            spend = card.get('signup_bonus_min_spend', 0.0)
            months = card.get('signup_bonus_max_months', 3)
            
            if points > 0:
                logger.info(f"  -> Signup bonus: {points:,} points")
            if value > 0.0:
                logger.info(f"  -> Signup value: ${value:,.0f}")
            if spend > 0.0:
                logger.info(f"  -> Min spend: ${spend:,.0f} in {months} months")
    
    # Save the fixed data
    output_file = output_path or file_path
    
    # Update extraction summary if it exists
    if isinstance(data, dict) and 'extraction_summary' in data:
        data['extraction_summary']['cards_with_intro_offers'] = len([
            c for c in cards 
            if c.get('signup_bonus_points', 0) > 0 or c.get('signup_bonus_value', 0.0) > 0
        ])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Fixed {fixed_count}/{total_cards} cards in {output_file}")

def main():
    """Main function to fix signup bonus parsing."""
    parser = argparse.ArgumentParser(description='Fix signup bonus parsing in existing JSON files')
    parser.add_argument('files', nargs='*', help='JSON files to fix (if none specified, processes recent output files)')
    parser.add_argument('--output-dir', help='Output directory for fixed files')
    args = parser.parse_args()
    
    if args.files:
        files_to_process = args.files
    else:
        # Find recent output files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'data', 'output')
        
        if os.path.exists(output_dir):
            files_to_process = []
            for filename in os.listdir(output_dir):
                if filename.endswith('.json') and ('nerdwallet' in filename or 'cards' in filename):
                    files_to_process.append(os.path.join(output_dir, filename))
        else:
            files_to_process = []
    
    if not files_to_process:
        logger.error("No files to process. Please specify JSON files or ensure output directory exists.")
        return
    
    for file_path in files_to_process:
        try:
            output_path = None
            if args.output_dir:
                filename = os.path.basename(file_path)
                output_path = os.path.join(args.output_dir, f"fixed_{filename}")
                os.makedirs(args.output_dir, exist_ok=True)
            
            fix_json_file(file_path, output_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    logger.info("Signup bonus parsing fix completed!")

if __name__ == "__main__":
    main() 
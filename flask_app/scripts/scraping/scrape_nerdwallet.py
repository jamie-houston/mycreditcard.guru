#!/usr/bin/env python3
"""
Main NerdWallet Credit Card Scraper

This script scrapes credit card data from NerdWallet HTML files and saves timestamped results.
It serves as the primary entry point for NerdWallet data collection.

Usage:
    python scrape_nerdwallet.py [--input FILE] [--output-dir DIR]

The script reads HTML files from data/input/ and saves timestamped JSON files to flask_app/data/output/
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add the flask_app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the detailed table scraper
from scrape_nerdwallet_table_detailed import scrape_nerdwallet_table, logger


def find_input_files(input_dir: str) -> list:
    """Find all HTML files in the input directory."""
    input_path = Path(input_dir)
    if not input_path.exists():
        return []
    
    html_files = list(input_path.glob("*.html"))
    return sorted(html_files)


def main():
    """Main function for the NerdWallet scraper."""
    parser = argparse.ArgumentParser(description='Scrape credit card data from NerdWallet HTML files')
    parser.add_argument('--input', '-i', type=str, 
                       help='Specific HTML file to process (default: auto-detect from data/input/)')
    parser.add_argument('--output-dir', '-o', type=str,
                       help='Output directory for JSON files (default: flask_app/data/output/)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress detailed output')
    
    args = parser.parse_args()
    
    # Determine paths
    base_dir = Path(__file__).parent.parent.parent.parent
    
    if args.input:
        input_files = [Path(args.input)]
    else:
        input_dir = base_dir / 'data' / 'input'
        input_files = find_input_files(input_dir)
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = base_dir / 'flask_app' / 'data' / 'output'
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_files:
        print("❌ No HTML files found to process")
        print(f"   Expected location: {base_dir / 'data' / 'input'}")
        print("   Please save NerdWallet HTML files there first")
        return 1
    
    if not args.quiet:
        print("🚀 NerdWallet Credit Card Scraper")
        print("=" * 50)
        print(f"📁 Input files: {len(input_files)}")
        print(f"📂 Output directory: {output_dir}")
        print()
    
    total_cards = 0
    processed_files = 0
    
    for input_file in input_files:
        if not input_file.exists():
            print(f"⚠️  File not found: {input_file}")
            continue
        
        if not args.quiet:
            print(f"📄 Processing: {input_file.name}")
        
        try:
            # Read HTML content
            with open(input_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Scrape the data
            cards = scrape_nerdwallet_table(html_content)
            
            if not cards:
                print(f"⚠️  No cards found in {input_file.name}")
                continue
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M')
            source_name = input_file.stem.replace('nerdwallet_', '').replace('_table', '')
            output_filename = f"{timestamp}_nerdwallet_{source_name}_cards.json"
            output_file = output_dir / output_filename
            
            # Prepare results with metadata
            results = {
                'extraction_summary': {
                    'total_cards': len(cards),
                    'cards_with_reward_categories': len([c for c in cards if c.get('reward_categories')]),
                    'cards_with_reward_tooltips': len([c for c in cards if c.get('rewards_tooltip')]),
                    'cards_with_intro_offers': len([c for c in cards if c.get('signup_bonus_points', 0) > 0 or c.get('signup_bonus_value', 0) > 0]),
                    'extraction_method': 'table_html_parsing',
                    'source_file': input_file.name,
                    'extraction_timestamp': datetime.now().isoformat()
                },
                'cards': cards
            }
            
            # Save results
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            total_cards += len(cards)
            processed_files += 1
            
            if not args.quiet:
                print(f"   ✅ Extracted {len(cards)} cards")
                print(f"   💾 Saved to: {output_filename}")
                
                # Show summary stats
                cards_with_rewards = len([c for c in cards if c.get('reward_categories')])
                cards_with_bonuses = len([c for c in cards if c.get('signup_bonus_points', 0) > 0])
                print(f"   📊 {cards_with_rewards} cards with reward categories")
                print(f"   🎁 {cards_with_bonuses} cards with signup bonuses")
                print()
            
        except Exception as e:
            print(f"❌ Error processing {input_file.name}: {e}")
            continue
    
    # Final summary
    if not args.quiet:
        print("=" * 50)
        print("📈 SCRAPING COMPLETE")
        print("=" * 50)
        print(f"📁 Files processed: {processed_files}")
        print(f"🏷️  Total cards extracted: {total_cards}")
        print(f"📂 Output directory: {output_dir}")
        print()
        
        if processed_files > 0:
            print("🎯 Next steps:")
            print("   1. Review the generated JSON files")
            print("   2. Import to database using:")
            print("      cd flask_app && python scripts/data/seed_credit_cards.py --import-scraped")
            print("   3. Or use the web interface: Credit Cards → Import Cards → Import from Files")
        else:
            print("⚠️  No files were successfully processed")
            print("   Check that HTML files exist in data/input/ and contain NerdWallet table data")
    
    return 0 if processed_files > 0 else 1


if __name__ == '__main__':
    sys.exit(main()) 
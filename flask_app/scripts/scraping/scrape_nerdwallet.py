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

# Import the detailed table scraper with categorization
from scrape_nerdwallet_table_detailed import scrape_nerdwallet_table, categorize_cards, logger


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
    
    # Initialize counters
    total_cards = 0
    processed_files = 0
    successful_files = 0
    failed_files = 0
    file_results = []
    
    for input_file in input_files:
        if not input_file.exists():
            print(f"⚠️  File not found: {input_file}")
            failed_files += 1
            file_results.append({
                'file': input_file.name,
                'status': 'not_found',
                'cards': 0,
                'error': 'File not found'
            })
            continue
        
        if not args.quiet:
            print(f"📄 Processing: {input_file.name}")
        
        try:
            # Read HTML content
            with open(input_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Scrape the data - avoid any database operations
            cards = scrape_nerdwallet_table(html_content)
            
            if not cards:
                print(f"⚠️  No cards found in {input_file.name}")
                failed_files += 1
                file_results.append({
                    'file': input_file.name,
                    'status': 'no_cards',
                    'cards': 0,
                    'error': 'No cards extracted from HTML'
                })
                continue
            
            # Apply categorization to separate valid and problematic cards
            try:
                if not args.quiet:
                    print(f"   🔍 Categorizing cards by issuer availability...")
                categorization = categorize_cards(cards)
                
                valid_cards = categorization['valid_cards']
                problematic_cards = categorization['problematic_cards']
                available_issuers = categorization['available_issuers']
                
                if not args.quiet:
                    print(f"   ✅ Valid cards: {len(valid_cards)}")
                    print(f"   ⚠️  Problematic cards: {len(problematic_cards)}")
                
            except Exception as e:
                # If categorization fails, fall back to old format
                logger.warning(f"Categorization failed, using old format: {e}")
                valid_cards = cards
                problematic_cards = []
                available_issuers = []
                
                if not args.quiet:
                    print(f"   ⚠️  Categorization failed, using all cards as valid")
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M')
            source_name = input_file.stem.replace('nerdwallet_', '').replace('_table', '')
            output_filename = f"{timestamp}_nerdwallet_{source_name}_cards.json"
            output_file = output_dir / output_filename
            
            # Analyze results for valid cards
            valid_cards_with_rewards = [c for c in valid_cards if c.get('reward_categories')]
            valid_cards_with_tooltips = [c for c in valid_cards if c.get('rewards_tooltip')]
            valid_cards_with_intro_offers = [c for c in valid_cards if c.get('signup_bonus_points', 0) > 0 or c.get('signup_bonus_value', 0) > 0]
            
            # Analyze issues in problematic cards
            issue_summary = {}
            for card in problematic_cards:
                for issue in card.get('issues', []):
                    issue_summary[issue] = issue_summary.get(issue, 0) + 1
            
            # Prepare results with new categorized format
            results = {
                'extraction_summary': {
                    'total_cards_extracted': len(cards),
                    'valid_cards_count': len(valid_cards),
                    'problematic_cards_count': len(problematic_cards),
                    'valid_cards_with_reward_categories': len(valid_cards_with_rewards),
                    'valid_cards_with_reward_tooltips': len(valid_cards_with_tooltips),
                    'valid_cards_with_intro_offers': len(valid_cards_with_intro_offers),
                    'issue_summary': issue_summary,
                    'available_issuers': available_issuers,
                    'extraction_method': 'table_html_parsing_with_issuer_validation',
                    'source_file': input_file.name,
                    'extraction_timestamp': datetime.now().isoformat()
                },
                'valid_cards': valid_cards,
                'problematic_cards': problematic_cards
            }
            
            # Save results
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            total_cards += len(cards)
            processed_files += 1
            successful_files += 1
            
            file_results.append({
                'file': input_file.name,
                'status': 'success',
                'total_cards': len(cards),
                'valid_cards': len(valid_cards),
                'problematic_cards': len(problematic_cards),
                'output_file': output_filename
            })
            
            if not args.quiet:
                print(f"   ✅ Extracted {len(cards)} total cards")
                print(f"   💾 Saved to: {output_filename}")
                
                # Show summary stats for valid cards
                print(f"   📊 {len(valid_cards_with_rewards)} valid cards with reward categories")
                print(f"   🎁 {len(valid_cards_with_intro_offers)} valid cards with signup bonuses")
                
                # Show issues summary if any
                if problematic_cards and issue_summary:
                    print(f"   ⚠️  Issues found:")
                    for issue, count in issue_summary.items():
                        print(f"      • {issue.replace('_', ' ').title()}: {count}")
                print()
            
        except Exception as e:
            print(f"❌ Error processing {input_file.name}: {e}")
            failed_files += 1
            file_results.append({
                'file': input_file.name,
                'status': 'error',
                'cards': 0,
                'error': str(e)
            })
            continue
    
    # Final summary with success/failure counts
    if not args.quiet:
        print("=" * 50)
        print("📈 SCRAPING COMPLETE")
        print("=" * 50)
        print(f"📁 Total files processed: {processed_files}")
        print(f"✅ Successful files: {successful_files}")
        print(f"❌ Failed files: {failed_files}")
        print(f"🏷️  Total cards extracted: {total_cards}")
        print(f"📂 Output directory: {output_dir}")
        print()
        
        # Show detailed results
        if file_results:
            print("📋 DETAILED RESULTS:")
            print("-" * 30)
            for result in file_results:
                status_icon = "✅" if result['status'] == 'success' else "❌"
                if result['status'] == 'success':
                    total = result.get('total_cards', result.get('cards', 0))  # backwards compatibility
                    valid = result.get('valid_cards', 0)
                    problematic = result.get('problematic_cards', 0)
                    print(f"{status_icon} {result['file']}: {total} total ({valid} valid, {problematic} problematic)")
                else:
                    cards = result.get('cards', 0)
                    print(f"{status_icon} {result['file']}: {cards} cards")
                    print(f"   Error: {result.get('error', 'Unknown error')}")
            print()
        
        if successful_files > 0:
            print("🎯 Next steps:")
            print("   1. Review the generated JSON files")
            print("   2. Import to database using:")
            print("      cd flask_app && python scripts/data/seed_credit_cards.py --import-scraped")
            print("   3. Or use the web interface: Credit Cards → Import Cards → Import from Files")
        else:
            print("⚠️  No files were successfully processed")
            print("   Check that HTML files exist in data/input/ and contain NerdWallet table data")
    else:
        # Quiet mode - just show the summary counts
        print(f"Processed: {processed_files}, Success: {successful_files}, Failed: {failed_files}, Cards: {total_cards}")
    
    return 0 if successful_files > 0 else 1


if __name__ == '__main__':
    sys.exit(main()) 
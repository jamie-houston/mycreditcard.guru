#!/usr/bin/env python3
"""
Guided Credit Card Data Scraping Workflow

This script provides a step-by-step guided workflow for scraping credit card data
from NerdWallet HTML files and importing them into the database. Perfect for users
who want a streamlined experience without remembering command-line options.

The workflow includes:
1. File selection for scraping
2. Running the scraper with progress feedback
3. File selection for importing
4. Running the import with validation

Usage:
    python guided_scraping.py
"""

import sys
import os
import subprocess
from pathlib import Path
import json
from datetime import datetime


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*80}")
    print(f"🎯 {title}")
    print(f"{'='*80}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'─'*60}")
    print(f"📋 {title}")
    print(f"{'─'*60}")


def get_input_files():
    """Get available HTML files for scraping."""
    input_dir = Path("../data/input")
    if not input_dir.exists():
        return []
    
    html_files = list(input_dir.glob("*.html"))
    return sorted(html_files)


def get_output_files():
    """Get available JSON files for importing."""
    output_dir = Path("data/output")
    if not output_dir.exists():
        return []
    
    json_files = list(output_dir.glob("*.json"))
    return sorted(json_files, reverse=True)  # Newest first


def show_file_selection(files, file_type="files"):
    """Show file selection menu."""
    if not files:
        print(f"❌ No {file_type} found.")
        return None
    
    print(f"\nAvailable {file_type}:")
    for i, file_path in enumerate(files, 1):
        file_size = file_path.stat().st_size
        size_str = f"{file_size/1024:.1f}KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f}MB"
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {i:2d}. {file_path.name} ({size_str}, modified {mod_time})")
    
    print(f"  {len(files)+1:2d}. All files")
    print(f"  {len(files)+2:2d}. Skip this step")
    
    return files


def get_user_selection(files, prompt="Select file"):
    """Get user's file selection."""
    try:
        choice = input(f"\n{prompt} (1-{len(files)+2}): ").strip()
        
        if not choice:
            return "skip"
        
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(files):
                return [files[choice_num - 1]]
            elif choice_num == len(files) + 1:
                return files  # All files
            elif choice_num == len(files) + 2:
                return "skip"
        
        print("❌ Invalid selection. Please try again.")
        return None
        
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Goodbye!")
        sys.exit(0)


def run_scraper(input_files):
    """Run the NerdWallet scraper on selected files."""
    print_section("Running NerdWallet Scraper")
    
    cmd = [sys.executable, "scripts/scraping/scrape_nerdwallet.py"]
    
    if len(input_files) == 1:
        cmd.extend(["--input", str(input_files[0])])
        print(f"🚀 Scraping: {input_files[0].name}")
    else:
        print(f"🚀 Scraping {len(input_files)} files...")
    
    try:
        result = subprocess.run(cmd, check=True, cwd=Path.cwd())
        print(f"\n✅ Scraping completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Scraping failed with exit code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error during scraping: {e}")
        return False


def show_scraped_file_info(json_file):
    """Show information about a scraped JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        cards = data.get('cards', [])
        metadata = data.get('metadata', {})
        
        print(f"    📊 {len(cards)} cards extracted")
        if 'extraction_timestamp' in metadata:
            print(f"    🕒 Extracted: {metadata['extraction_timestamp']}")
        if 'source_file' in metadata:
            print(f"    📄 Source: {metadata['source_file']}")
        
        # Count cards with rewards
        cards_with_rewards = sum(1 for card in cards if card.get('reward_categories'))
        if cards_with_rewards > 0:
            print(f"    🎁 {cards_with_rewards} cards with detailed rewards")
            
    except Exception as e:
        print(f"    ⚠️  Could not read file info: {e}")


def run_importer(json_files):
    """Run the credit card importer on selected files."""
    print_section("Running Credit Card Importer")
    
    cmd = [sys.executable, "scripts/data/seed_credit_cards.py", "--import-scraped"]
    
    if len(json_files) == 1:
        cmd.extend(["--file", str(json_files[0])])
        print(f"🚀 Importing: {json_files[0].name}")
        show_scraped_file_info(json_files[0])
    else:
        print(f"🚀 Importing {len(json_files)} files chronologically...")
        for json_file in json_files:
            print(f"  📄 {json_file.name}")
            show_scraped_file_info(json_file)
    
    try:
        result = subprocess.run(cmd, check=True, cwd=Path.cwd())
        print(f"\n✅ Import completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Import failed with exit code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error during import: {e}")
        return False


def main():
    """Main guided workflow."""
    print_header("Guided Credit Card Data Scraping Workflow")
    
    print("Welcome to the guided scraping workflow! 🎉")
    print("This will walk you through scraping NerdWallet data and importing it to the database.")
    print("\nWhat we'll do:")
    print("  1. 🔍 Select HTML files to scrape")
    print("  2. 🚀 Run the scraper to extract credit card data")
    print("  3. 📊 Select JSON files to import")
    print("  4. 💾 Import the data into the database")
    
    # Step 1: File Selection for Scraping
    print_section("Step 1: Select Files to Scrape")
    input_files = get_input_files()
    
    if not input_files:
        print("❌ No HTML files found in data/input/")
        print("💡 Please add NerdWallet HTML files to data/input/ directory first.")
        sys.exit(1)
    
    selected_input_files = None
    while selected_input_files is None:
        files_to_show = show_file_selection(input_files, "HTML files")
        if files_to_show is None:
            sys.exit(1)
        selected_input_files = get_user_selection(files_to_show, "Select files to scrape")
    
    if selected_input_files == "skip":
        print("⏭️  Skipping scraping step...")
    else:
        # Step 2: Run Scraper
        scraping_success = run_scraper(selected_input_files)
        if not scraping_success:
            print("\n⚠️  Scraping failed. You can still proceed with importing existing files.")
    
    # Step 3: File Selection for Importing
    print_section("Step 3: Select Files to Import")
    output_files = get_output_files()
    
    if not output_files:
        print("❌ No JSON files found in data/output/")
        if selected_input_files == "skip":
            print("💡 Run the scraper first to generate JSON files.")
            sys.exit(1)
        else:
            print("💡 The scraper should have created files. Check data/output/ directory.")
            sys.exit(1)
    
    selected_output_files = None
    while selected_output_files is None:
        files_to_show = show_file_selection(output_files, "JSON files")
        if files_to_show is None:
            sys.exit(1)
        selected_output_files = get_user_selection(files_to_show, "Select files to import")
    
    if selected_output_files == "skip":
        print("⏭️  Skipping import step...")
        print("✅ Workflow completed. Files are ready for manual import.")
    else:
        # Step 4: Run Importer
        import_success = run_importer(selected_output_files)
        
        if import_success:
            print_section("🎉 Workflow Completed Successfully!")
            print("Your credit card data has been scraped and imported.")
            print("\n💡 Next steps:")
            print("  • Visit the web interface to view imported cards")
            print("  • Run tests to verify data integrity: python flask_app/run_tests.py")
            print("  • Create recommendations using the imported data")
        else:
            print_section("⚠️  Workflow Completed with Errors")
            print("Scraping was successful, but import had issues.")
            print("Check the error messages above and try importing manually.")
    
    print(f"\n{'='*80}")
    print("Thanks for using the guided workflow! 🚀")
    print("Remember: 'The best credit card is the one you actually use responsibly!' 💳")


if __name__ == "__main__":
    main() 
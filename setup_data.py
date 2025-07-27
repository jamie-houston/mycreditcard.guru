#!/usr/bin/env python
"""
Setup script to load all initial data for Credit Card Guru.
Run this after fresh database migration.
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

def run_command(command, description):
    """Run a management command and handle errors gracefully."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} completed successfully")
        if result.stdout.strip():
            # Show important output lines
            lines = result.stdout.strip().split('\n')
            for line in lines[-3:]:  # Show last 3 lines
                if line.strip():
                    print(f"   {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   {e.stderr}")
        return False

def main():
    """Load all initial data for the application."""
    print("🚀 Setting up Credit Card Guru with initial data...")
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check for virtual environment
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  Warning: No virtual environment detected. Make sure dependencies are installed.")
    
    success_count = 0
    total_commands = 0
    
    # 1. Load system data
    system_files = [
        'data/input/system/spending_categories.json',
        'data/input/system/issuers.json', 
        'data/input/system/reward_types.json'
    ]
    
    for file_path in system_files:
        if os.path.exists(file_path):
            total_commands += 1
            if run_command(f'python manage.py loaddata {file_path}', f'Loading {Path(file_path).name}'):
                success_count += 1
        else:
            print(f"⚠️  Warning: {file_path} not found, skipping...")
    
    # 2. Import credit cards from all available files
    card_files = glob.glob('data/input/cards/*.json')
    # Exclude personal.json as it's often a template
    card_files = [f for f in card_files if not f.endswith('personal.json')]
    
    if card_files:
        print(f"\n📋 Found {len(card_files)} card files to import...")
        for card_file in sorted(card_files):
            total_commands += 1
            issuer_name = Path(card_file).stem.replace('_', ' ').title()
            if run_command(f'python manage.py import_cards {card_file}', f'Importing {issuer_name} cards'):
                success_count += 1
    else:
        print("⚠️  Warning: No card files found in data/input/cards/")
    
    # 3. Import credit types (offers/benefits)
    total_commands += 1
    if run_command('python manage.py import_credit_types', 'Importing credit types (offers/benefits)'):
        success_count += 1
    
    # Summary
    print(f"\n🎯 Setup Summary:")
    print(f"   ✅ {success_count}/{total_commands} commands completed successfully")
    
    if success_count == total_commands:
        print(f"\n🎉 All data loaded successfully!")
        print(f"   • System data: spending categories, issuers, reward types")
        print(f"   • Credit cards: {len(card_files)} issuer files")
        print(f"   • Credit types: offers and benefits for roadmap preferences")
        print(f"\nYou can now:")
        print(f"   • Run: python manage.py runserver")
        print(f"   • Visit: http://127.0.0.1:8000/")
        print(f"   • Create roadmaps with full credit preferences!")
    else:
        print(f"\n⚠️  Some commands failed. Check the errors above.")
        print(f"   You may need to:")
        print(f"   • Run migrations first: python manage.py migrate")
        print(f"   • Check file paths are correct")
        print(f"   • Ensure virtual environment is activated")

if __name__ == '__main__':
    main() 
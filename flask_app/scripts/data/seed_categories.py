#!/usr/bin/env python
"""Script to seed database with default categories for credit card rewards and optionally import cards."""

import os
import sys
import glob
from pathlib import Path

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models.category import Category

# Default categories commonly used in credit card rewards
DEFAULT_CATEGORIES = [
    {
        'name': 'dining',
        'display_name': 'Dining & Restaurants',
        'description': 'Restaurants, bars, cafes, and food delivery services',
        'icon': 'fas fa-utensils',
        'sort_order': 10,
        'aliases': ['restaurants', 'restaurant', 'dining at restaurants', 'takeout', 'delivery service', 'dining & restaurants']
    },
    {
        'name': 'travel',
        'display_name': 'Travel',
        'description': 'Airlines, hotels, rental cars, and travel booking services',
        'icon': 'fas fa-plane',
        'sort_order': 20,
        'aliases': ['travel purchases', 'travel purchased', 'other travel', 'travel booked', 'hotels', 'hotel', 'rental cars', 'car rentals', 'flights', 'airfare', 'attractions', 'southwest purchases']
    },
    {
        'name': 'groceries',
        'display_name': 'Groceries',
        'description': 'Supermarkets and grocery stores',
        'icon': 'fas fa-shopping-cart',
        'sort_order': 30,
        'aliases': ['grocery', 'grocery stores', 'supermarkets', 'wholesale clubs']
    },
    {
        'name': 'gas',
        'display_name': 'Gas Stations',
        'description': 'Gas stations and fuel purchases',
        'icon': 'fas fa-gas-pump',
        'sort_order': 40,
        'aliases': ['gas stations', 'gasoline', 'fuel']
    },
    {
        'name': 'entertainment',
        'display_name': 'Entertainment',
        'description': 'Movies, concerts, streaming services, and entertainment venues',
        'icon': 'fas fa-film',
        'sort_order': 50,
        'aliases': []
    },
    {
        'name': 'shopping',
        'display_name': 'Shopping',
        'description': 'Online and retail shopping, department stores',
        'icon': 'fas fa-shopping-bag',
        'sort_order': 60,
        'aliases': ['online retail', 'online purchases']
    },
    {
        'name': 'transportation',
        'display_name': 'Transportation',
        'description': 'Public transit, taxis, rideshare services',
        'icon': 'fas fa-car',
        'sort_order': 70,
        'aliases': ['transit', 'rideshare', 'parking', 'tolls', 'trains', 'buses', 'public transit', 'subway', 'bus', 'metro']
    },
    {
        'name': 'streaming',
        'display_name': 'Streaming Services',
        'description': 'Video and music streaming subscriptions',
        'icon': 'fas fa-tv',
        'sort_order': 80,
        'aliases': ['streaming services', 'select streaming services', 'streaming subscriptions']
    },
    {
        'name': 'drugstores',
        'display_name': 'Drugstores & Pharmacies',
        'description': 'Pharmacies and health-related purchases',
        'icon': 'fas fa-pills',
        'sort_order': 90,
        'aliases': ['drugstore', 'pharmacy']
    },
    {
        'name': 'home_improvement',
        'display_name': 'Home Improvement',
        'description': 'Hardware stores, home improvement retailers',
        'icon': 'fas fa-home',
        'sort_order': 100,
        'aliases': []
    },
    {
        'name': 'office_supplies',
        'display_name': 'Office Supplies',
        'description': 'Office supply stores and business expenses',
        'icon': 'fas fa-briefcase',
        'sort_order': 110,
        'aliases': []
    },
    {
        'name': 'telecommunications',
        'display_name': 'Telecommunications',
        'description': 'Phone, internet, and cable services',
        'icon': 'fas fa-phone',
        'sort_order': 120,
        'aliases': ['internet', 'phone', 'cable', 'cell phone', 'wireless']
    },
    {
        'name': 'utilities',
        'display_name': 'Utilities',
        'description': 'Electricity, water, gas, internet, phone, and other utility bills',
        'icon': 'fas fa-bolt',
        'sort_order': 125,
        'aliases': []
    },
    {
        'name': 'amazon',
        'display_name': 'Amazon',
        'description': 'Amazon purchases',
        'icon': 'fab fa-amazon',
        'sort_order': 150,
        'aliases': []
    },
    {
        'name': 'other',
        'display_name': 'Other',
        'description': 'Any expenses that don\'t fit into the above categories',
        'icon': 'fas fa-ellipsis-h',
        'sort_order': 140,
        'aliases': ['all purchases', 'everything else', 'everything', 'all other purchases', 'base rate', 'base', 'base rate']
    },
    # {
    #     'name': 'healthcare',
    #     'display_name': 'Healthcare',
    #     'description': 'Medical expenses, prescriptions, and insurance payments',
    #     'icon': 'fas fa-heartbeat',
    #     'sort_order': 130,
    #     'aliases': []
    # },
    # {
    #     'name': 'education',
    #     'display_name': 'Education',
    #     'description': 'Tuition, books, courses, and education-related expenses',
    #     'icon': 'fas fa-graduation-cap',
    #     'sort_order': 135,
    #     'aliases': []
    # },
    # {
    #     'name': 'paypal',
    #     'display_name': 'PayPal',
    #     'description': 'PayPal purchases and transactions',
    #     'icon': 'fab fa-paypal',
    #     'sort_order': 145,
    #     'aliases': []
    # },
    # {
    #     'name': 'online_groceries',
    #     'display_name': 'Online Groceries',
    #     'description': 'Online grocery delivery services and apps',
    #     'icon': 'fas fa-shopping-cart',
    #     'sort_order': 35,
    #     'aliases': ['online grocery', 'grocery delivery', 'online grocery delivery']
    # },
]

def seed_categories():
    """Seed the database with default categories."""
    created_count = 0
    updated_count = 0
    
    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        
        if existing:
            # Update existing category with new data (but keep active status)
            existing.display_name = cat_data['display_name']
            existing.description = cat_data['description']
            existing.icon = cat_data['icon']
            existing.sort_order = cat_data['sort_order']
            existing.set_aliases(cat_data.get('aliases', []))
            updated_count += 1
        else:
            # Create new category
            category = Category(
                name=cat_data['name'],
                display_name=cat_data['display_name'],
                description=cat_data['description'],
                icon=cat_data['icon'],
                sort_order=cat_data['sort_order'],
                is_active=True
            )
            category.set_aliases(cat_data.get('aliases', []))
            db.session.add(category)
            created_count += 1
    
    db.session.commit()
    print(f"✅ Seeded {created_count} categories, updated {updated_count} existing")
    return created_count

def find_newest_output_file():
    """Find the newest JSON file in the data/output directory."""
    output_dir = Path(__file__).parent.parent.parent.parent / 'flask_app' / 'data' / 'output'
    
    if not output_dir.exists():
        print(f"📁 Output directory not found: {output_dir}")
        return None
    
    # Find all JSON files in the output directory
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        print(f"📄 No JSON files found in {output_dir}")
        return None
    
    # Sort by modification time and get the newest
    newest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    print(f"🔍 Found newest output file: {newest_file.name}")
    return newest_file

def import_sample_cards():
    """Import some sample credit cards if no output files are available."""
    from seed_credit_cards import seed_credit_cards
    print("🎯 Importing sample credit cards...")
    return seed_credit_cards()

def import_cards_from_output():
    """Import cards from the newest output file."""
    from import_cards import import_cards
    
    newest_file = find_newest_output_file()
    
    if newest_file:
        print(f"📥 Importing cards from: {newest_file.name}")
        try:
            import_cards(json_file=str(newest_file))
            print("✅ Cards imported successfully!")
            return True
        except Exception as e:
            print(f"❌ Error importing cards: {e}")
            print("🔄 Falling back to sample cards...")
            return import_sample_cards()
    else:
        print("📂 No output files found, importing sample cards...")
        return import_sample_cards()

def main():
    """Main function to seed categories and optionally import cards."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed categories and optionally import cards')
    parser.add_argument('--import-cards', action='store_true', 
                       help='Import cards from newest output file or sample cards')
    parser.add_argument('--sample-only', action='store_true',
                       help='Only import sample cards, skip checking output files')
    
    args = parser.parse_args()
    
    app = create_app('development')
    with app.app_context():
        # Always seed categories first
        print("🏷️  Seeding categories...")
        created_categories = seed_categories()
        
        # Import cards if requested
        if args.import_cards or args.sample_only:
            print("\n" + "="*50)
            if args.sample_only:
                import_sample_cards()
            else:
                import_cards_from_output()
        else:
            print(f"\n💡 To also import cards, run with --import-cards")
            print(f"   Example: python {Path(__file__).name} --import-cards")
        
        return 0

if __name__ == '__main__':
    sys.exit(main()) 
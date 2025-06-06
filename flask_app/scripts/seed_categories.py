#!/usr/bin/env python
"""Script to seed database with default categories for credit card rewards."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.category import Category

# Default categories commonly used in credit card rewards
DEFAULT_CATEGORIES = [
    {
        'name': 'dining',
        'display_name': 'Dining & Restaurants',
        'description': 'Restaurants, bars, cafes, and food delivery services',
        'icon': 'fas fa-utensils',
        'sort_order': 10
    },
    {
        'name': 'travel',
        'display_name': 'Travel',
        'description': 'Airlines, hotels, rental cars, and travel booking services',
        'icon': 'fas fa-plane',
        'sort_order': 20
    },
    {
        'name': 'groceries',
        'display_name': 'Groceries',
        'description': 'Supermarkets and grocery stores',
        'icon': 'fas fa-shopping-cart',
        'sort_order': 30
    },
    {
        'name': 'gas',
        'display_name': 'Gas Stations',
        'description': 'Gas stations and fuel purchases',
        'icon': 'fas fa-gas-pump',
        'sort_order': 40
    },
    {
        'name': 'entertainment',
        'display_name': 'Entertainment',
        'description': 'Movies, concerts, streaming services, and entertainment venues',
        'icon': 'fas fa-film',
        'sort_order': 50
    },
    {
        'name': 'shopping',
        'display_name': 'Shopping',
        'description': 'Online and retail shopping, department stores',
        'icon': 'fas fa-shopping-bag',
        'sort_order': 60
    },
    {
        'name': 'transportation',
        'display_name': 'Transportation',
        'description': 'Public transit, taxis, rideshare services',
        'icon': 'fas fa-car',
        'sort_order': 70
    },
    {
        'name': 'streaming',
        'display_name': 'Streaming Services',
        'description': 'Video and music streaming subscriptions',
        'icon': 'fas fa-tv',
        'sort_order': 80
    },
    {
        'name': 'drugstores',
        'display_name': 'Drugstores & Pharmacies',
        'description': 'Pharmacies and health-related purchases',
        'icon': 'fas fa-pills',
        'sort_order': 90
    },
    {
        'name': 'home_improvement',
        'display_name': 'Home Improvement',
        'description': 'Hardware stores, home improvement retailers',
        'icon': 'fas fa-home',
        'sort_order': 100
    },
    {
        'name': 'office_supplies',
        'display_name': 'Office Supplies',
        'description': 'Office supply stores and business expenses',
        'icon': 'fas fa-briefcase',
        'sort_order': 110
    },
    {
        'name': 'telecommunications',
        'display_name': 'Telecommunications',
        'description': 'Phone, internet, and cable services',
        'icon': 'fas fa-phone',
        'sort_order': 120
    },
    {
        'name': 'base',
        'display_name': 'Base Rate',
        'description': 'Default rate for all other purchases',
        'icon': 'fas fa-percentage',
        'sort_order': 0
    }
]

def seed_categories():
    """Create default categories if they don't exist."""
    app = create_app('default')
    
    with app.app_context():
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
                updated_count += 1
                print(f"Updated category: {cat_data['display_name']}")
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
                db.session.add(category)
                created_count += 1
                print(f"Created category: {cat_data['display_name']}")
        
        try:
            db.session.commit()
            print(f"\nSeeding completed! Created {created_count} new categories, updated {updated_count} existing categories.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding categories: {e}")

if __name__ == '__main__':
    seed_categories() 
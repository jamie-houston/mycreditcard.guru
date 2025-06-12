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
        'sort_order': 10,
        'aliases': ['restaurants', 'restaurant', 'dining at restaurants', 'takeout', 'delivery service']
    },
    {
        'name': 'travel',
        'display_name': 'Travel',
        'description': 'Airlines, hotels, rental cars, and travel booking services',
        'icon': 'fas fa-plane',
        'sort_order': 20,
        'aliases': ['travel purchases', 'travel purchased', 'other travel', 'travel booked', 'hotels', 'hotel', 'rental cars', 'car rentals', 'flights', 'airfare', 'attractions']
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
        'name': 'online_groceries',
        'display_name': 'Online Groceries',
        'description': 'Online grocery delivery services and apps',
        'icon': 'fas fa-shopping-cart',
        'sort_order': 35,
        'aliases': ['online grocery', 'grocery delivery', 'online grocery delivery']
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
        'aliases': ['transit', 'rideshare', 'parking', 'tolls', 'trains', 'buses']
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
        'aliases': []
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
        'name': 'healthcare',
        'display_name': 'Healthcare',
        'description': 'Medical expenses, prescriptions, and insurance payments',
        'icon': 'fas fa-heartbeat',
        'sort_order': 130,
        'aliases': []
    },
    {
        'name': 'education',
        'display_name': 'Education',
        'description': 'Tuition, books, courses, and education-related expenses',
        'icon': 'fas fa-graduation-cap',
        'sort_order': 135,
        'aliases': []
    },
    {
        'name': 'other',
        'display_name': 'Other',
        'description': 'Any expenses that don\'t fit into the above categories',
        'icon': 'fas fa-ellipsis-h',
        'sort_order': 140,
        'aliases': ['all purchases', 'everything else', 'everything', 'all other purchases', 'base rate', 'base']
    },
    {
        'name': 'paypal',
        'display_name': 'PayPal',
        'description': 'PayPal purchases and transactions',
        'icon': 'fab fa-paypal',
        'sort_order': 145,
        'aliases': []
    },
    {
        'name': 'amazon',
        'display_name': 'Amazon',
        'description': 'Amazon purchases',
        'icon': 'fab fa-amazon',
        'sort_order': 150,
        'aliases': []
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
                existing.set_aliases(cat_data.get('aliases', []))
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
                category.set_aliases(cat_data.get('aliases', []))
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
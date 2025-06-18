#!/usr/bin/env python
"""
Seed Card Issuers

This script seeds the database with sample card issuers.
"""

import sys
import os

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models import CardIssuer

def seed_issuers():
    """Seed the database with card issuers."""
    issuers_data = [
        # Major US Credit Card Issuers (always include)
        'Chase',
        'Capital One', 
        'American Express',
        'Bank of America',
        'Citi',
    ]
    ignored_issuers = [
        # Additional issuers commonly found in scraped data
        'Discover',
        'Wells Fargo',
        'U.S. Bank',
        'Barclays',
        'HSBC',
        'PNC Bank',
        'TD Bank',
        'USAA',
        'Navy Federal Credit Union',
        'Alliant Credit Union',
        'Synchrony Bank',
        'Marcus by Goldman Sachs',
        'Citizens Bank',
        'Fifth Third Bank',
        'Regions Bank',
        'SunTrust Bank',
        'BB&T',
        'KeyBank',
        'Huntington Bank',
        'First National Bank',
        'BMO Harris Bank',
        'BBVA',
        'Comerica Bank',
        'Zions Bank'
    ]
    
    created_count = 0
    updated_count = 0
    
    for name in issuers_data:
        existing_issuer = CardIssuer.query.filter_by(name=name).first()
        if not existing_issuer:
            issuer = CardIssuer(name=name)
            db.session.add(issuer)
            created_count += 1
            print(f"✅ Created issuer: {name}")
        else:
            updated_count += 1
            print(f"⏭️  Skipped existing issuer: {name}")
    
    db.session.commit()
    print(f"\n📊 Summary:")
    print(f"✅ Created {created_count} new card issuers")
    print(f"⏭️  Skipped {updated_count} existing issuers")
    print(f"🏦 Total issuers in database: {created_count + updated_count}")
    
    return created_count

def main():
    """Main function to seed issuers."""
    app = create_app('development')
    with app.app_context():
        return seed_issuers()

if __name__ == "__main__":
    sys.exit(main()) 
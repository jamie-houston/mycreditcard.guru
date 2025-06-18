#!/usr/bin/env python3
"""
Create Phase 2 database tables manually.
"""
import os
import sys
from pathlib import Path

# Add the Flask app to the Python path
current_dir = Path(__file__).parent
flask_app_dir = current_dir.parent.parent
sys.path.insert(0, str(flask_app_dir))

from app import create_app, db
from app.models.user_card import UserCard
from app.models.issuer_policy import IssuerPolicy

def create_phase2_tables():
    """Create the Phase 2 database tables."""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("🏗️  Creating Phase 2 database tables...")
            
            # Create all tables
            db.create_all()
            
            print("✅ Phase 2 tables created successfully!")
            print("📊 Tables created:")
            print("   - user_cards (UserCard model)")
            print("   - issuer_policies (IssuerPolicy model)")
            
        except Exception as e:
            print(f"❌ Error creating Phase 2 tables: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    create_phase2_tables()
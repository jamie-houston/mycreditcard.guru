#!/usr/bin/env python3
"""
Create database migration for Phase 2 models.
"""
import os
import sys
from pathlib import Path

# Add the Flask app to the Python path
current_dir = Path(__file__).parent
flask_app_dir = current_dir.parent.parent
sys.path.insert(0, str(flask_app_dir))

from app import create_app, db
from flask_migrate import upgrade, init, migrate, revision

def create_migration():
    """Create a new migration for the Phase 2 models."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Create migration
            revision(message="Add UserCard and IssuerPolicy models for Phase 2 roadmap functionality", autogenerate=True)
            print("✅ Migration created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating migration: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    create_migration()
#!/usr/bin/env python
"""
Database Initializer

This script creates all database tables based on the current SQLAlchemy models.
Use this for initial database setup or when you need to create tables without migrations.
"""

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.user_data import UserProfile
from app.models.user import User
from app.models.recommendation import Recommendation

def init_db():
    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    init_db() 
#!/usr/bin/env python
"""
Test User Creator

This script creates test user accounts for development purposes.
Creates both admin and regular user accounts with default credentials.
"""

from app import create_app, db
from app.models.user import User
import uuid

def create_test_users():
    app = create_app()
    with app.app_context():
        # Create admin user
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password='adminpass',
                is_admin=True
            )
            db.session.add(admin)
            print("Admin user created.")
        else:
            print("Admin user already exists.")

        # Create regular test user
        test_user = User.query.filter_by(email='user@example.com').first()
        if not test_user:
            test_user = User(
                username='testuser',
                email='user@example.com',
                password='userpass'
            )
            db.session.add(test_user)
            print("Test user created.")
        else:
            print("Test user already exists.")

        db.session.commit()
        
        print("\nTest users created successfully!")
        print("Admin login: admin@example.com / adminpass")
        print("User login: user@example.com / userpass")

if __name__ == "__main__":
    create_test_users() 
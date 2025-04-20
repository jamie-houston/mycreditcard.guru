#!/usr/bin/env python
import os
from app import create_app, db
from app.models.user import User
from app.models.profile import CreditCardProfile
from app.models.credit_card import CreditCard
from app.models.category import Category
from app.models.goal import Goal

def init_db():
    # Create a Flask app with the appropriate config
    app = create_app(os.getenv('FLASK_CONFIG') or 'development')

    # Push an application context to make the app aware of the db operations
    with app.app_context():
        # Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating all tables...")
        db.create_all()
        
        # Create an admin user
        print("Creating admin user...")
        admin = User(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_admin=True
        )
        
        # Create demo user
        print("Creating demo user...")
        demo = User(
            username='demo',
            email='demo@demo.com',
            password='test1234',
            is_admin=False
        )
        
        db.session.add(admin)
        db.session.add(demo)
        db.session.commit()
        
        print("Database initialization completed successfully!")
        print(f"Admin user created. Username: admin, Password: admin123")
        print(f"Demo user created. Username: demo, Email: demo@demo.com, Password: test1234")

if __name__ == '__main__':
    init_db() 
from app import create_app, db
from app.models.user import User
from datetime import datetime
import os
import sqlite3
from pathlib import Path

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

# Check if database exists and initialize if needed
def init_database():
    # Check if database exists
    db_path = Path("app.db")
    db_exists = db_path.exists()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if users table is empty
        user_count = User.query.count()
        if user_count == 0:
            print("Creating default users...")
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password='admin123',
                is_admin=True
            )
            
            # Create demo user
            demo = User(
                username='demo',
                email='demo@demo.com',
                password='test1234',
                is_admin=False
            )
            
            db.session.add(admin)
            db.session.add(demo)
            db.session.commit()
            print("Default users created")

# Initialize database when app starts
init_database()

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db)

# Add a health check route to test if the app is working
@app.route('/health')
def health_check():
    return {'status': 'ok', 'db_status': 'connected', 'time': str(datetime.utcnow())}

if __name__ == '__main__':
    app.run(debug=True) 
from app import create_app
from app.extensions import db, migrate

app = create_app()

# This exposes the app, db, and migrate for Flask CLI
# Flask-Migrate will auto-register the 'db' command

if __name__ == '__main__':
    manager.run() 
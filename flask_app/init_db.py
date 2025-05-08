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
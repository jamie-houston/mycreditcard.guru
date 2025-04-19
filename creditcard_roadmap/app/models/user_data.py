from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # User spending data
    total_monthly_spend = db.Column(db.Float, default=0.0)
    
    # Category spending as JSON
    # Format: {"gas": 200.0, "groceries": 500.0, "dining": 300.0, ...}
    category_spending = db.Column(db.Text, default='{}')
    
    # Reward preferences as JSON
    # Format: ["travel", "cash_back", ...]
    reward_preferences = db.Column(db.Text, default='[]')
    
    # Additional user preferences
    max_annual_fees = db.Column(db.Float, default=0.0)  # Maximum annual fees willing to pay
    max_cards = db.Column(db.Integer, default=5)  # Maximum number of cards
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserProfile {self.id} with ${self.total_monthly_spend}/month spend>'

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    
    # Recommendation details as JSON
    # Format: [
    #   {
    #     "card_id": 1, 
    #     "signup_month": 1,
    #     "cancel_month": 12,
    #     "estimated_value": 1000.0
    #   },
    # ]
    recommendation_data = db.Column(db.Text, nullable=False)
    
    total_estimated_value = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_profile = db.relationship('UserProfile', backref=db.backref('recommendations', lazy=True))
    
    def __repr__(self):
        return f'<Recommendation {self.id} for user {self.user_profile_id}>' 
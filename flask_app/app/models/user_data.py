from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
import json

class UserProfile(db.Model):
    """User profile model for storing spending data."""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(36), nullable=True, index=True)  # To link anonymous profiles
    name = db.Column(db.String(100), nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Float, nullable=False)
    total_monthly_spend = db.Column(db.Float, nullable=False)
    category_spending = db.Column(db.Text, nullable=False)  # JSON string
    reward_preferences = db.Column(db.Text, nullable=True)  # JSON string for reward preferences
    max_cards = db.Column(db.Integer, default=1)
    max_annual_fees = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with recommendations - without backref
    recommendations = db.relationship('app.models.recommendation.Recommendation', lazy=True, 
                                     foreign_keys='app.models.recommendation.Recommendation.user_profile_id')
    
    def get_category_spending(self):
        """Parse and return the category spending as a dictionary."""
        try:
            return json.loads(self.category_spending)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_category_spending(self, spending_dict):
        """Convert dictionary to JSON string and set category_spending."""
        self.category_spending = json.dumps(spending_dict)
    
    def get_reward_preferences(self):
        """Parse and return the reward preferences as a list."""
        try:
            return json.loads(self.reward_preferences)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_reward_preferences(self, preferences_list):
        """Convert list to JSON string and set reward_preferences."""
        self.reward_preferences = json.dumps(preferences_list)
    
    def calculate_total_spend(self):
        """Calculate the total monthly spend from category spending."""
        spending = self.get_category_spending()
        return sum(spending.values())
    
    @classmethod
    def get_profiles_for_user_or_session(cls, user_id=None, session_id=None):
        """Get profiles for either a logged-in user or anonymous session."""
        if user_id:
            return cls.query.filter_by(user_id=user_id).all()
        elif session_id:
            return cls.query.filter_by(session_id=session_id).all()
        return []
    
    def __repr__(self):
        return f"<UserProfile {self.name}, Credit Score: {self.credit_score}>"

# Remove duplicate Recommendation model
# It should only be defined in app/models/recommendation.py 
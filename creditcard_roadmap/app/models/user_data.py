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
    name = db.Column(db.String(100), nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Float, nullable=False)
    total_monthly_spend = db.Column(db.Float, nullable=False)
    category_spending = db.Column(db.Text, nullable=False)  # JSON string
    max_cards = db.Column(db.Integer, default=5)
    max_annual_fees = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with recommendations - without backref
    recommendations = db.relationship('app.models.recommendation.Recommendation', lazy=True, 
                                     foreign_keys='app.models.recommendation.Recommendation.profile_id')
    
    def get_category_spending(self):
        """Parse and return the category spending as a dictionary."""
        try:
            return json.loads(self.category_spending)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_category_spending(self, spending_dict):
        """Convert dictionary to JSON string and set category_spending."""
        self.category_spending = json.dumps(spending_dict)
    
    def calculate_total_spend(self):
        """Calculate the total monthly spend from category spending."""
        spending = self.get_category_spending()
        return sum(spending.values())
    
    def __repr__(self):
        return f"<UserProfile {self.name}, Credit Score: {self.credit_score}>"

class Recommendation(db.Model):
    """Model for storing generated recommendations."""
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    recommendation_data = db.Column(db.Text, nullable=False)  # JSON string
    total_value = db.Column(db.Float, nullable=False)
    total_annual_fees = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_recommendation_data(self):
        """Parse and return the recommendation data as a dictionary."""
        try:
            return json.loads(self.recommendation_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_net_value(self):
        """Calculate the net value (total value - annual fees)."""
        return self.total_value - self.total_annual_fees
    
    def get_recommended_cards(self):
        """Get the list of recommended card IDs."""
        data = self.get_recommendation_data()
        if data and 'card_details' in data:
            return list(data['card_details'].keys())
        return []
    
    def __repr__(self):
        return f"<Recommendation {self.id}, Value: ${self.total_value:.2f}>" 
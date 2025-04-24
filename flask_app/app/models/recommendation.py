from app import db
import json
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict, MutableList

class Recommendation(db.Model):
    """Model for credit card recommendations"""
    
    __tablename__ = 'recommendations'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    
    # Store spending profile as JSON string
    _spending_profile = db.Column(db.Text, nullable=True)
    # Store card preferences as JSON string
    _card_preferences = db.Column(db.Text, nullable=True)
    
    # Store the recommended sequence of card applications
    _recommended_sequence = db.Column(db.Text, nullable=False)
    
    # Store details about each card's value
    _card_details = db.Column(db.Text, nullable=False)
    
    # Total values
    total_value = db.Column(db.Float, nullable=False)
    total_annual_fees = db.Column(db.Float, nullable=False)
    
    # Monthly breakdown of value over time
    _per_month_value = db.Column(db.Text, nullable=True)
    
    # Count of cards in the recommendation
    card_count = db.Column(db.Integer, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships with fully qualified paths
    user = db.relationship('app.models.user.User', backref=db.backref('user_recommendations', lazy=True))

    profile = db.relationship('app.models.user_data.UserProfile', foreign_keys=[user_profile_id], overlaps="recommendations")
    
    # Property accessors
    @property
    def spending_profile(self):
        """Get spending profile dict from JSON"""
        if self._spending_profile:
            return json.loads(self._spending_profile)
        return {}
    
    @spending_profile.setter
    def spending_profile(self, value):
        """Store spending profile as JSON"""
        if value is None:
            self._spending_profile = json.dumps({})
        else:
            self._spending_profile = json.dumps(value)
    
    @property
    def card_preferences(self):
        """Get card preferences dict from JSON"""
        if self._card_preferences:
            return json.loads(self._card_preferences)
        return {}
    
    @card_preferences.setter
    def card_preferences(self, value):
        """Store card preferences as JSON"""
        if value is None:
            self._card_preferences = json.dumps({})
        else:
            self._card_preferences = json.dumps(value)
    
    @property
    def recommended_sequence(self):
        """Get recommended card sequence from JSON"""
        if self._recommended_sequence:
            return json.loads(self._recommended_sequence)
        return []
    
    @recommended_sequence.setter
    def recommended_sequence(self, value):
        """Store recommended card sequence as JSON"""
        if value is None:
            self._recommended_sequence = json.dumps([])
        else:
            self._recommended_sequence = json.dumps(value)
    
    @property
    def card_details(self):
        """Get card details from JSON"""
        if self._card_details:
            return json.loads(self._card_details)
        return {}
    
    @card_details.setter
    def card_details(self, value):
        """Store card details as JSON"""
        if value is None:
            self._card_details = json.dumps({})
        else:
            self._card_details = json.dumps(value)
    
    @property
    def per_month_value(self):
        """Get monthly value breakdown from JSON"""
        if self._per_month_value:
            return json.loads(self._per_month_value)
        return []
    
    @per_month_value.setter
    def per_month_value(self, value):
        """Store monthly value breakdown as JSON"""
        if value is None:
            self._per_month_value = json.dumps([])
        else:
            self._per_month_value = json.dumps(value)
    
    def __repr__(self):
        return f'<Recommendation {self.id} for User {self.user_id}>' 
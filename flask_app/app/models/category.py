from app import db
from datetime import datetime

class Category(db.Model):
    """Model for expense categories."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Metadata
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Category {self.name}>' 
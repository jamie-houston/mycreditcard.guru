from datetime import datetime
import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager

class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # User role: 0 = standard user, 1 = admin
    role = db.Column(db.Integer, default=0)
    
    # Profile information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    
    # Account metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    spending_profiles = db.relationship('UserProfile', backref='user', lazy='dynamic', 
                                       foreign_keys='UserProfile.user_id')
    
    def __init__(self, username, email, password, is_admin=False):
        """Initialize a new user."""
        self.public_id = str(uuid.uuid4())
        self.username = username
        self.email = email
        self.set_password(password)
        if is_admin:
            self.role = 1
    
    @property
    def password(self):
        """Prevent password from being accessed."""
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set the password hash from a plain text password."""
        self.password_hash = generate_password_hash(password)
        
    def set_password(self, password):
        """Set the password hash from a plain text password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 1
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'public_id': self.public_id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.get(int(user_id))
    
    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_public_id(cls, public_id):
        return cls.query.filter_by(public_id=public_id).first()
    
    def __repr__(self):
        """String representation of the user."""
        return f'<User {self.username}>'
    
    @property
    def is_authenticated(self):
        """Return True as all registered users are authenticated."""
        return True
        
    @property
    def is_active(self):
        """Return True as all users are active by default."""
        return True
        
    @property
    def is_anonymous(self):
        """Return False as anonymous users are not supported."""
        return False
        
    def get_id(self):
        """Return the user ID as a unicode string."""
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    """Load a user given the user id."""
    return User.get_by_id(user_id) 
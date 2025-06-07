import os
from flask import Flask, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, AnonymousUserMixin, current_user
from config import Config
from app.extensions import csrf
from flask_wtf.csrf import CSRFProtect
import json
from datetime import datetime
import uuid
from markupsafe import Markup

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.google.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access admin features.'
csrf = CSRFProtect()

# Create an anonymous user class with the same interface as User
class AnonymousUser(AnonymousUserMixin):
    id = None
    username = 'Anonymous'
    email = None
    role = 0  # Standard user role
    
    @property
    def is_anonymous(self):
        return True
    
    @property
    def is_admin(self):
        return False
    
    def get_id(self):
        # For anonymous users, use a session-based ID
        if 'anonymous_user_id' not in session:
            session['anonymous_user_id'] = str(uuid.uuid4())
        return session['anonymous_user_id']

# Set the anonymous user class
login_manager.anonymous_user = AnonymousUser

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///creditcard_roadmap.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    # Load config overrides if specified
    if config_name:
        app.config.from_object(Config)
    
    # Initialize Flask extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register custom Jinja filters
    @app.template_filter('json_parse')
    def json_parse_filter(value):
        """Parse JSON string to Python object"""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    # Configure Jinja environment
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    
    # Register blueprints
    from app.routes.main import main
    
    app.register_blueprint(main)
    
    # Register auth blueprint
    from app.blueprints.auth import auth
    app.register_blueprint(auth)
    
    from app.routes.credit_cards import credit_cards as credit_cards_blueprint
    app.register_blueprint(credit_cards_blueprint, url_prefix='/credit_cards')
    
    from app.routes.user_data import user_data as user_data_blueprint
    app.register_blueprint(user_data_blueprint, url_prefix='/profile')
    
    from app.routes.recommendations import recommendations as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint, url_prefix='/recommendations')
    
    # Register admin blueprint
    from app.blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    # Add template context processors
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow,
            'is_admin': lambda: current_user.is_authenticated and getattr(current_user, 'role', 0) == 1,
            'is_anonymous': lambda: current_user.is_anonymous,
        }
    
    # Initialize the database if it doesn't exist
    with app.app_context():
        db.create_all()
    
    return app 
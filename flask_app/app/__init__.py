import os
import logging
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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging to suppress OAuth warnings that users shouldn't see
logging.getLogger('flask_dance').setLevel(logging.ERROR)
logging.getLogger('oauthlib').setLevel(logging.ERROR)
logging.getLogger('requests_oauthlib').setLevel(logging.ERROR)

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
        from config import config
        config_class = config.get(config_name, Config)
        app.config.from_object(config_class)
        
    # Set up logging
    logger = logging.getLogger('creditcard_roadmap')
    
    # Log configuration for debugging
    logger.info(f"App initialized with config: {config_name}")
    logger.info(f"Session settings: PERMANENT_SESSION_LIFETIME={app.config.get('PERMANENT_SESSION_LIFETIME')}")
    logger.info(f"Remember cookie: REMEMBER_COOKIE_DURATION={app.config.get('REMEMBER_COOKIE_DURATION')}")
    
    # Make sure session is permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True
        # Log session info for debugging
        if current_user.is_authenticated:
            logger.info(f"Request from authenticated user: {current_user.username}")
        elif 'user_id' in session:
            logger.info(f"Session has user_id but user not authenticated: {session.get('user_id')}")
    
    # Initialize Flask extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        try:
            # Convert to int since get_id() returns a string
            user_id_int = int(user_id)
            user = User.query.get(user_id_int)
            if user:
                logger.info(f"User loader found user: {user.username} (ID: {user_id})")
            else:
                logger.warning(f"User loader could not find user with ID: {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error in user_loader: {str(e)}", exc_info=True)
            return None
    
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
    
    from app.blueprints.recommendations import bp as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint)
    
    # Register admin blueprint
    from app.blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    # Register categories blueprint
    from app.routes.categories import categories as categories_blueprint
    app.register_blueprint(categories_blueprint)
    
    from app.routes.issuers import issuers as issuers_blueprint
    app.register_blueprint(issuers_blueprint, url_prefix='/issuers')
    
    # Register roadmap blueprint
    from app.routes.roadmap import roadmap as roadmap_blueprint
    app.register_blueprint(roadmap_blueprint, url_prefix='/roadmap')
    
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
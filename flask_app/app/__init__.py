import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from app.extensions import csrf
from flask_wtf.csrf import CSRFProtect
import json
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()

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
    from app.routes.auth import auth
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    from app.routes.credit_cards import credit_cards as credit_cards_blueprint
    app.register_blueprint(credit_cards_blueprint, url_prefix='/credit_cards')
    
    from app.routes.user_data import user_data as user_data_blueprint
    app.register_blueprint(user_data_blueprint, url_prefix='/profile')
    
    from app.routes.recommendations import recommendations as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint, url_prefix='/recommendations')
    
    # Add template context processors
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow
        }
    
    # Initialize the database if it doesn't exist
    with app.app_context():
        db.create_all()
    
    return app 
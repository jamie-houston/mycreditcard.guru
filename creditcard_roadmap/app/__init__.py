import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from app.extensions import csrf

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(__name__)
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
    
    # Register blueprints
    from app.routes.main import main
    from app.routes.auth import auth
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    from app.routes.credit_cards import credit_cards as credit_cards_blueprint
    app.register_blueprint(credit_cards_blueprint, url_prefix='/cards')
    
    from app.routes.user_data import user_data as user_data_blueprint
    app.register_blueprint(user_data_blueprint, url_prefix='/profile')
    
    from app.routes.recommendations import recommendations as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint, url_prefix='/recommendations')
    
    return app 
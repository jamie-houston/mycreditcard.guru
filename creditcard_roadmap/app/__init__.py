from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

from config import config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.routes.credit_cards import credit_cards as credit_cards_blueprint
    app.register_blueprint(credit_cards_blueprint, url_prefix='/cards')
    
    from app.routes.user_data import user_data as user_data_blueprint
    app.register_blueprint(user_data_blueprint, url_prefix='/user')
    
    from app.routes.recommendations import recommendations as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint, url_prefix='/recommendations')
    
    return app 
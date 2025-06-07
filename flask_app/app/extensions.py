from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
import logging

# Set up logging
logger = logging.getLogger('creditcard_roadmap')

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in with Google to access this page.'
login_manager.login_message_category = 'info'

# Log configuration
logger.info("Flask extensions initialized")
logger.info(f"Login manager configured with login_view: {login_manager.login_view}") 
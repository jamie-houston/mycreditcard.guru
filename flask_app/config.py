import os
import tempfile
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login config
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
    
    # Session config
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_USE_SIGNER = True
    
    # Pagination
    CARDS_PER_PAGE = 12

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///creditcard_roadmap.db'

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a separate test database file instead of in-memory to avoid issues
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_creditcard_roadmap.db'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Safety check to ensure we're not accidentally using the development database
        if 'test' not in app.config.get('SQLALCHEMY_DATABASE_URI', '').lower():
            raise RuntimeError("Test configuration must use a test database! Current URI: " + 
                             app.config.get('SQLALCHEMY_DATABASE_URI', 'None'))

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///creditcard_roadmap.db'
    PREFERRED_URL_SCHEME = "https"
    SERVER_NAME = "www.mycreditcard.guru"

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 
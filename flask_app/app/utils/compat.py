"""
SQLAlchemy Compatibility Layer
This module provides a compatibility layer for using SQLAlchemy 2.x patterns
while keeping backward compatibility with SQLAlchemy 1.4.x.
"""

import contextlib
import functools
from app import db

# SQLAlchemy compatibility functions

def safe_query(model):
    """
    Provide a safe query interface that works with both SQLAlchemy 1.4 and 2.0
    
    Usage:
        users = safe_query(User).filter_by(active=True).all()
        
    Will use model.query.filter_by() in 1.4 and db.session.query(model) in 2.0
    """
    try:
        import sqlalchemy
        version = sqlalchemy.__version__
        if version.startswith('1.'):
            # SQLAlchemy 1.x style
            return model.query
        else:
            # SQLAlchemy 2.x style
            return db.session.query(model)
    except Exception:
        # Default to 2.x style as it's more future-proof
        return db.session.query(model)

@contextlib.contextmanager
def safe_commit():
    """
    Provide a safe context manager for session operations
    
    Usage:
        with safe_commit():
            db.session.add(user)
    """
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def safe_commit_decorator(f):
    """
    Decorator to safely commit database changes
    
    Usage:
        @safe_commit_decorator
        def create_user(username, email):
            user = User(username=username, email=email)
            db.session.add(user)
            return user
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            raise e
    return decorated_function 
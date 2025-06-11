from flask import Blueprint, render_template, redirect, url_for, session, jsonify
from flask_login import current_user

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Landing page of the application."""
    # Redirect logged-in users to their profile page
    if current_user.is_authenticated:
        return redirect(url_for('user_data.profile'))
    
    # Show welcome/dashboard page for non-logged-in users
    return render_template('index.html', title='My Credit Card Guru')

@main.route('/debug')
def debug():
    """Public debug route to check auth status"""
    debug_data = {
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if hasattr(current_user, 'get_id') else None,
        'session_keys': list(session.keys()) if session else [],
        'user_info': {
            'username': getattr(current_user, 'username', None),
            'email': getattr(current_user, 'email', None),
            'id': getattr(current_user, 'id', None),
        } if hasattr(current_user, 'username') else None,
    }
    return jsonify(debug_data) 
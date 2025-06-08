from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
import os
import logging
from app import db
from app.models.user import User

# Create the authentication blueprint
auth = Blueprint('auth', __name__)

# Set up logging
logger = logging.getLogger('creditcard_roadmap')

# Google OAuth blueprint
def create_oauth_blueprint():
    # Configure OAuth for security
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    logger.info("Set OAUTHLIB_RELAX_TOKEN_SCOPE=1")
    
    # Set OAUTHLIB_INSECURE_TRANSPORT for local/dev
    server_name = os.environ.get('SERVER_NAME')
    if server_name and not server_name.startswith('localhost'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
    else:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    try:
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
        if not client_id or not client_secret:
            logger.error("Missing Google OAuth credentials")
            raise ValueError("Missing Google OAuth credentials. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET")
        logger.info(f"Creating Google blueprint with client_id: {client_id[:10]}...")
        blueprint = make_google_blueprint(
            client_id=client_id,
            client_secret=client_secret,
            scope=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ],
            redirect_to='auth.authorized'  # Use dynamic URL generation
        )
        logger.info("Google OAuth blueprint created successfully")
        return blueprint
    except Exception as e:
        logger.error(f"Error creating OAuth blueprint: {str(e)}", exc_info=True)
        raise

# Initialize the OAuth blueprint
try:
    google_bp = create_oauth_blueprint()
    auth.register_blueprint(google_bp, url_prefix="/login")
    logger.info("Registered Google OAuth blueprint with auth blueprint")
except Exception as e:
    logger.error(f"Failed to register OAuth blueprint: {str(e)}", exc_info=True)
    raise

@auth.route('/login')
def login():
    """Redirect to Google OAuth login page"""
    logger.info("Login route accessed, redirecting to Google OAuth")
    
    # Check if user is already logged in
    if current_user.is_authenticated:
        logger.info(f"User already logged in as {current_user.username}, redirecting to index")
        return redirect(url_for('main.index'))
        
    # Clear any stale session data
    if 'google_oauth_token' in session:
        logger.info("Clearing stale OAuth token from session")
        session.pop('google_oauth_token', None)
        
    return redirect(url_for('auth.google.login'))

# This handles the redirect back from Google OAuth
@auth.route('/authorized')
def authorized():
    """Handle the OAuth callback after Google authorization"""
    logger.info("OAuth authorized route accessed")
    
    # Add a direct check for Google authorization
    if not google.authorized:
        logger.warning("Google not authorized in the authorized route")
        flash("Google login failed or was cancelled.", "danger")
        return redirect(url_for('main.index'))
    
    try:
        # Try to get user info
        logger.info("Attempting to get user info from Google")
        resp = google.get("/oauth2/v2/userinfo")
        
        if not resp.ok:
            logger.error(f"Failed to get user info: {resp.status_code} - {resp.text}")
            flash("Failed to get user info from Google.", "danger")
            return redirect(url_for('main.index'))
        
        # Successfully got user info
        user_info = resp.json()
        logger.info(f"Got user info from Google: {user_info.get('email')}")
        
        email = user_info.get('email')
        if not email:
            logger.error("No email found in Google response")
            flash("No email provided by Google.", "danger")
            return redirect(url_for('main.index'))
        
        # Look up the user
        user = User.query.filter_by(email=email).first()
        is_admin = email.lower() == 'foresterh@gmail.com'
        
        # Create user if not found
        if not user:
            username = email.split('@')[0] + str(User.query.count() + 1)
            user = User(username=username, email=email, password=os.urandom(16).hex(), is_admin=is_admin)
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new user: {username} with email: {email}")
            flash("Account created via Google login!", "success")
        else:
            logger.info(f"Found existing user: {user.username}")
            if is_admin and not user.is_admin:
                user.role = 1
                db.session.commit()
        
        # Log the user in
        session.permanent = True
        login_user(user, remember=True)
        user.update_last_login()
        
        # Store info in session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['logged_in_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"User authenticated: {user.username}, id: {user.id}")
        logger.info(f"Session keys: {list(session.keys())}")
        
        flash("Logged in with Google!", "success")
        return redirect(url_for('main.index'))
    
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}", exc_info=True)
        flash("An error occurred during login. Please try again.", "danger")
        return redirect(url_for('main.index'))

@auth.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    if current_user.is_authenticated:
        logger.info(f"Logging out user: {current_user.username}")
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    """Display user profile"""
    logger.info(f"Profile accessed by user: {current_user.username}")
    return render_template('auth/profile.html')

@auth.route('/debug-auth')
def debug_auth():
    """Debug route to check authentication status"""
    debug_info = {
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'username': current_user.username if current_user.is_authenticated else None,
        'google_authorized': google.authorized if hasattr(google, 'authorized') else None,
        'session_keys': list(session.keys()),
        'has_user_id_in_session': 'user_id' in session,
    }
    
    logger.info(f"Auth debug info: {debug_info}")
    
    return render_template('auth/debug.html', debug_info=debug_info)

@auth.route('/session-debug')
def session_debug():
    """Debug endpoint to check session state"""
    debug_data = {
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'username': current_user.username if current_user.is_authenticated else None,
        'session_keys': list(session.keys()),
        'session_data': {key: session.get(key) for key in session.keys() if key not in ['_csrf_token', 'csrf_token', '_id', '_fresh']},
        'google_authorized': google.authorized if hasattr(google, 'authorized') else None,
        'google_token': session.get('google_oauth_token') is not None
    }
    
    return jsonify(debug_data)

@auth.route('/test-login')
def test_login():
    """Test route to simulate login for debugging"""
    # Get or create a test user
    email = 'test@example.com'
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Create a test user
        username = 'testuser'
        user = User(username=username, email=email, password='password', is_admin=False)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Created test user: {username}")
    
    # Login the user
    session.permanent = True
    login_user(user, remember=True)
    user.update_last_login()
    
    # Store info in session
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['logged_in_at'] = datetime.utcnow().isoformat()
    
    logger.info(f"Test login for user: {user.username}, id: {user.id}")
    logger.info(f"Session keys after test login: {list(session.keys())}")
    
    flash("Test login successful!", "success")
    return redirect(url_for('main.index')) 
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
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
    
    # Set up redirect URL for PythonAnywhere
    redirect_url = None
    pythonanywhere_domain = os.environ.get('PYTHONANYWHERE_DOMAIN')
    
    if pythonanywhere_domain:
        # We're on PythonAnywhere with a custom domain
        redirect_url = f"https://{pythonanywhere_domain}/login/google/authorized"
        logger.info(f"Setting OAuth redirect URL to: {redirect_url}")
        
        # Make sure Flask-Dance knows we're using HTTPS
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
        logger.info("Set OAUTHLIB_INSECURE_TRANSPORT=0 for production")
        
        # Important: set the reputed_uri to use the custom domain
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    else:
        # Local development - allow HTTP
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        logger.info("Set OAUTHLIB_INSECURE_TRANSPORT=1 for development")
    
    # Create the blueprint - don't specify redirect_to to use default Flask-Dance routing
    try:
        logger.info(f"Creating Google blueprint with client_id: {os.environ.get('GOOGLE_OAUTH_CLIENT_ID')[:10]}...")
        logger.info(f"Redirect URL: {redirect_url}")
        
        blueprint = make_google_blueprint(
            client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
            scope=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ],
            redirect_url=redirect_url,
            # Set reputed_uri to fix the redirect issues
            reputed_uri=redirect_url if redirect_url else None
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
    return redirect(url_for('google.login'))

# This route handles the OAuth callback
@auth.route('/oauth-complete')
def oauth_complete():
    """Complete the login process after Google OAuth"""
    logger.info("OAuth complete route accessed")
    
    if not google.authorized:
        logger.warning("OAuth complete called but not authorized")
        flash("Google login failed or was cancelled.", "danger")
        return redirect(url_for('main.index'))

    try:
        logger.info("Fetching user info from Google")
        resp = google.get("/oauth2/v2/userinfo")
        
        if not resp.ok:
            logger.error(f"Failed to fetch user info: {resp.status_code} - {resp.text}")
            flash("Failed to fetch user info from Google.", "danger")
            return redirect(url_for('main.index'))

        info = resp.json()
        logger.info(f"User info fetched successfully for email: {info.get('email')}")
        
        email = info["email"]
        user = User.query.filter_by(email=email).first()
        
        # Check if this is the admin user
        is_admin_email = email.lower() == 'foresterh@gmail.com'
        
        if not user:
            # Create a new user with a random username
            username = email.split('@')[0] + str(User.query.count() + 1)
            user = User(username=username, email=email, password=os.urandom(16).hex(), is_admin=is_admin_email)
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new user: {username} with email: {email}")
            flash("Account created via Google login!", "success")
            if is_admin_email:
                logger.info("Admin user logged in")
                flash("Welcome, admin!", "info")
        else:
            logger.info(f"Existing user logged in: {user.username}")
            # Update existing user to admin if needed
            if is_admin_email and not user.is_admin:
                user.role = 1  # Set admin role
                db.session.commit()
                logger.info("Granted admin privileges to user")
                flash("Admin privileges granted!", "info")
        
        login_user(user)
        user.update_last_login()
        flash("Logged in with Google!", "success")
        logger.info(f"Successfully logged in user: {user.username}")
        return redirect(url_for('main.index'))
    
    except Exception as e:
        logger.error(f"OAuth error: {str(e)}", exc_info=True)
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
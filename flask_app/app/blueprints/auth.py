from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
import os
from app import db
from app.models.user import User

# Create the authentication blueprint
auth = Blueprint('auth', __name__)

# Google OAuth blueprint
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for local dev

google_bp = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)

auth.register_blueprint(google_bp, url_prefix="/login")

@auth.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    """Display user profile"""
    return render_template('auth/profile.html')

@auth.route('/login/google')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for('main.index'))
    info = resp.json()
    email = info["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create a new user with a random username
        username = email.split('@')[0] + str(User.query.count() + 1)
        user = User(username=username, email=email, password=os.urandom(16).hex())
        db.session.add(user)
        db.session.commit()
        flash("Account created via Google login!", "success")
    login_user(user)
    user.update_last_login()
    flash("Logged in with Google!", "success")
    return redirect(url_for('main.dashboard'))

@auth.route('/login/google/authorized')
def google_authorized():
    if not google.authorized:
        flash("Google login failed or was cancelled.", "danger")
        return redirect(url_for('main.index'))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for('main.index'))
    info = resp.json()
    email = info["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        username = email.split('@')[0] + str(User.query.count() + 1)
        user = User(username=username, email=email, password=os.urandom(16).hex())
        db.session.add(user)
        db.session.commit()
        flash("Account created via Google login!", "success")
    login_user(user)
    user.update_last_login()
    flash("Logged in with Google!", "success")
    return redirect(url_for('main.dashboard')) 
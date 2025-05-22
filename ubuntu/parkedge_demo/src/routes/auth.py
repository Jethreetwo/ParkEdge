import os
from flask import Blueprint, redirect, request, session, url_for, current_app, flash
from flask_login import login_user, logout_user, login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests # For fetching user info directly

from src.models.user import User
from src.models import db # Correctly import db

auth_bp = Blueprint('auth', __name__)

# Configuration - In a real app, these would be set in environment variables
# and loaded via app.config

# Updated to use app.config primarily, especially for testing
def get_google_client_id():
    if current_app.config.get('TESTING') and current_app.config.get('GOOGLE_CLIENT_ID'):
        return current_app.config['GOOGLE_CLIENT_ID']
    return os.environ.get("GOOGLE_CLIENT_ID")

def get_google_client_secret():
    if current_app.config.get('TESTING') and current_app.config.get('GOOGLE_CLIENT_SECRET'):
        return current_app.config['GOOGLE_CLIENT_SECRET']
    return os.environ.get("GOOGLE_CLIENT_SECRET")

def get_google_redirect_uri():
    if current_app.config.get('TESTING') and current_app.config.get('GOOGLE_REDIRECT_URI'):
        return current_app.config['GOOGLE_REDIRECT_URI']
    return os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/login/google/authorized")

# These will be dynamically fetched by the helper functions when needed
# GOOGLE_CLIENT_ID = None 
# GOOGLE_CLIENT_SECRET = None
# GOOGLE_REDIRECT_URI = None

# OAuth 2.0 scopes
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

@auth_bp.route('/login')
def login():
    # This is a placeholder for a potential manual login page
    # For now, it can redirect to Google login or show a message
    return redirect(url_for('auth.login_google'))

@auth_bp.route('/login/google')
def login_google():
    g_client_id = get_google_client_id()
    g_client_secret = get_google_client_secret()
    g_redirect_uri = get_google_redirect_uri()

    if not g_client_id or not g_client_secret:
        flash("Google Client ID or Secret not configured.", "error")
        return redirect(url_for('serve', path='')) # Redirect to home or an error page

    flow = Flow.from_client_config( 
        client_config={
            "web": {
                "client_id": g_client_id,
                "client_secret": g_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "issuer": "https://accounts.google.com", 
                "redirect_uris": [g_redirect_uri], 
                "userinfo_uri": "https://openidconnect.googleapis.com/v1/userinfo",
            }
        },
        scopes=SCOPES,
        redirect_uri=g_redirect_uri
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['oauth_state'] = state
    return redirect(authorization_url)

@auth_bp.route('/login/google/authorized')
def authorized():
    g_client_id = get_google_client_id()
    g_client_secret = get_google_client_secret()
    g_redirect_uri = get_google_redirect_uri()

    if not g_client_id or not g_client_secret:
        flash("Google Client ID or Secret not configured during callback.", "error")
        return redirect(url_for('serve', path=''))

    state = session.pop('oauth_state', None)
    if not state and current_app.config.get('TESTING') and request.args.get('state'):
        state = request.args.get('state') 

    if state is None or state != request.args.get('state'):
        flash("Invalid state parameter. CSRF Warning!", "error")
        return redirect(url_for('serve', path='')) 

    flow = Flow.from_client_config( 
         client_config={
            "web": {
                "client_id": g_client_id,
                "client_secret": g_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [g_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=g_redirect_uri
    )

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        current_app.logger.error(f"Failed to fetch token: {e}")
        flash(f"Failed to fetch OAuth token: {e}", "error")
        return redirect(url_for('auth.login'))

    if not flow.credentials:
        flash("Failed to obtain credentials.", "error")
        return redirect(url_for('auth.login'))

    try:
        id_info = id_token.verify_oauth2_token(
            flow.credentials.id_token, 
            google_requests.Request(session=requests.session()), 
            g_client_id 
        )
        
        google_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name")
        profile_pic = id_info.get("picture")

        if not email:
            flash("Email not provided by Google.", "error")
            return redirect(url_for('auth.login'))

        # Updated SQLAlchemy 2.0 syntax
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user is None:
            user = db.session.execute(db.select(User).filter_by(google_id=google_id)).scalar_one_or_none()
            
        if user:
            user.google_id = google_id 
            user.username = name 
            user.profile_pic = profile_pic 
        else:
            user = User(
                google_id=google_id,
                email=email,
                username=name, 
                profile_pic=profile_pic
            )
            db.session.add(user)
        
        db.session.commit()
        login_user(user, remember=True)
        flash("Successfully logged in with Google!", "success")
        return redirect(url_for('serve', path='map_view.html')) 

    except ValueError as e:
        current_app.logger.error(f"Invalid token: {e}")
        flash("Invalid authentication token from Google.", "error")
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Error during Google login: {e}")
        flash("An error occurred during Google login.", "error")
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('serve', path='')) 

@auth_bp.route('/status')
def status():
    if current_user.is_authenticated:
        return {
            "authenticated": True,
            "user": {
                "username": current_user.username,
                "email": current_user.email, 
                "profile_pic": current_user.profile_pic,
            }
        }
    else:
        return {"authenticated": False}

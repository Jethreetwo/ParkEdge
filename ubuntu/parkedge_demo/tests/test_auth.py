import pytest
from flask import session, url_for, current_app 
from flask_login import current_user
from unittest.mock import patch, MagicMock

from src.models.user import User
from src.models import db as _db 

# --- Google Login Tests (/auth/login/google) ---
def test_google_login_redirects(client, app): 
    app.config['GOOGLE_CLIENT_ID'] = "test_google_client_id"
    app.config['GOOGLE_CLIENT_SECRET'] = "test_google_client_secret"
    app.config['GOOGLE_REDIRECT_URI'] = "http://localhost/auth/login/google/authorized"

    with patch('google_auth_oauthlib.flow.Flow.authorization_url') as mock_auth_url:
        mock_auth_url.return_value = ("https://mock_google_auth_url.com", "mock_state")
        response = client.get(url_for('auth.login_google'))
        assert response.status_code == 302
        assert response.location == "https://mock_google_auth_url.com"
        with client.session_transaction() as sess:
            assert 'oauth_state' in sess
            assert sess['oauth_state'] == "mock_state"
        mock_auth_url.assert_called_once()

def test_google_login_missing_creds(client, app):
    original_client_id = app.config.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_ID'] = None 
    
    # Make request without following redirects to check session for flash
    response = client.get(url_for('auth.login_google'), follow_redirects=False)
    assert response.status_code == 302 # Should redirect
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert len(flashes) > 0
        assert flashes[0][0] == "error" # Category
        assert "Google Client ID or Secret not configured." in flashes[0][1] # Message
    
    # Optionally, check the final page content after redirect
    response_redirected = client.get(response.location) # Manually follow redirect
    assert response_redirected.status_code == 200 
    # Add assertion for final page content if flash messages are rendered there
    # For now, checking session is more direct for unit testing the route's action.

    app.config['GOOGLE_CLIENT_ID'] = original_client_id

# --- Google Callback Tests (/auth/login/google/authorized) ---
@patch('google_auth_oauthlib.flow.Flow.fetch_token')
@patch('google.oauth2.id_token.verify_oauth2_token')
def test_google_callback_new_user(mock_verify_id_token, mock_fetch_token, client, database, app): 
    with client.session_transaction() as sess: 
        sess['oauth_state'] = "test_state_value"
    mock_fetch_token.return_value = None 
    mock_credentials = MagicMock()
    mock_credentials.id_token = "mock_jwt_id_token"
    with patch('google_auth_oauthlib.flow.Flow.from_client_config') as mock_flow_init:
        mock_flow_instance = MagicMock()
        def side_effect_fetch_token(*args, **kwargs):
            mock_flow_instance.credentials = mock_credentials 
        mock_flow_instance.fetch_token.side_effect = side_effect_fetch_token
        mock_flow_init.return_value = mock_flow_instance
        mock_verify_id_token.return_value = {
            "iss": "accounts.google.com", "sub": "new_google_id_123",
            "email": "newuser@example.com", "name": "New User",
            "picture": "http://example.com/newuser.jpg", "email_verified": True
        }
        
        response_initial = client.get(url_for('auth.authorized', state="test_state_value", code="mock_auth_code"), follow_redirects=False)
        assert response_initial.status_code == 302 # Redirects to map_view.html
        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            assert len(flashes) > 0
            assert flashes[0][0] == "success"
            assert "Successfully logged in with Google!" in flashes[0][1]

        response_redirected = client.get(response_initial.location) # Manually follow redirect
        assert response_redirected.status_code == 200
        
        user_stmt = _db.select(User).filter_by(email="newuser@example.com") 
        user = database.session.execute(user_stmt).scalar_one_or_none() 
        assert user is not None
        assert user.google_id == "new_google_id_123"
        assert user.username == "New User"
        assert user.profile_pic == "http://example.com/newuser.jpg"
        
        with client: 
            client.get(url_for('auth.status')) 
            assert current_user.is_authenticated
            assert current_user.id == user.id

@patch('google_auth_oauthlib.flow.Flow.fetch_token')
@patch('google.oauth2.id_token.verify_oauth2_token')
def test_google_callback_existing_user_by_email(mock_verify_id_token, mock_fetch_token, client, database, test_user, app): 
    with client.session_transaction() as sess:
        sess['oauth_state'] = "test_state_value_existing"
    test_user_instance = database.session.get(User, test_user.id) 
    test_user_instance.google_id = None 
    database.session.commit()
    mock_fetch_token.return_value = None
    mock_credentials = MagicMock()
    mock_credentials.id_token = "mock_jwt_id_token_existing"
    with patch('google_auth_oauthlib.flow.Flow.from_client_config') as mock_flow_init:
        mock_flow_instance = MagicMock()
        def side_effect_fetch_token(*args, **kwargs):
            mock_flow_instance.credentials = mock_credentials
        mock_flow_instance.fetch_token.side_effect = side_effect_fetch_token
        mock_flow_init.return_value = mock_flow_instance
        mock_verify_id_token.return_value = {
            "iss": "accounts.google.com", "sub": "updated_google_id_for_existing_user", 
            "email": test_user_instance.email, "name": "Updated Name",
            "picture": "http://example.com/updated.jpg", "email_verified": True
        }
        
        response_initial = client.get(url_for('auth.authorized', state="test_state_value_existing", code="mock_auth_code_existing"), follow_redirects=False)
        assert response_initial.status_code == 302
        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            assert len(flashes) > 0
            assert flashes[0][0] == "success"
            assert "Successfully logged in with Google!" in flashes[0][1]

        response_redirected = client.get(response_initial.location)
        assert response_redirected.status_code == 200
        
        updated_user = database.session.get(User, test_user_instance.id) 
        assert updated_user.google_id == "updated_google_id_for_existing_user"
        assert updated_user.username == "Updated Name"
        assert updated_user.profile_pic == "http://example.com/updated.jpg"
        with client:
            client.get(url_for('auth.status'))
            assert current_user.is_authenticated
            assert current_user.id == test_user_instance.id

def test_google_callback_invalid_state(client, app):
    with client.session_transaction() as sess:
        sess['oauth_state'] = "correct_state_for_someone_else"
    
    response_initial = client.get(url_for('auth.authorized', state="wrong_state_for_this_user", code="mock_auth_code"), follow_redirects=False)
    assert response_initial.status_code == 302 
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert len(flashes) > 0
        assert flashes[0][0] == "error"
        assert "Invalid state parameter. CSRF Warning!" in flashes[0][1]

    with client:
        client.get(url_for('auth.status'))
        assert not current_user.is_authenticated

@patch('google_auth_oauthlib.flow.Flow.fetch_token', side_effect=Exception("Token fetch failed"))
def test_google_callback_token_fetch_failure(mock_fetch_token, client, app):
    with client.session_transaction() as sess:
        sess['oauth_state'] = "test_state_value"
        
    response_initial = client.get(url_for('auth.authorized', state="test_state_value", code="mock_auth_code"), follow_redirects=False)
    assert response_initial.status_code == 302 # Redirects to login
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert len(flashes) > 0
        assert flashes[0][0] == "error"
        assert "Failed to fetch OAuth token: Token fetch failed" in flashes[0][1]
        
    with client:
        client.get(url_for('auth.status'))
        assert not current_user.is_authenticated

# --- Logout Tests (/auth/logout) ---
def test_logout(logged_in_client, test_user, app): 
    response_initial = logged_in_client.get(url_for('auth.logout'), follow_redirects=False)
    assert response_initial.status_code == 302
    with logged_in_client.session_transaction() as sess: # Use logged_in_client here
        flashes = sess.get('_flashes', [])
        assert len(flashes) > 0
        assert flashes[0][0] == "info"
        assert "You have been logged out." in flashes[0][1]
        
    # Verify current_user is anonymous after logout
    # The logged_in_client fixture handles logout in its teardown,
    # so current_user might already be anonymous if checked with the same client instance
    # after the redirect. For a cleaner test, we check the session or use a fresh client context.
    
    # This check is after the redirect would have happened and session cleared by flask-login logout_user
    response_redirected = logged_in_client.get(response_initial.location) # Follow redirect
    assert response_redirected.status_code == 200

    # To verify current_user state post-logout, it's best to use the client to make a new request
    # The logged_in_client fixture itself will call logout_user in its teardown.
    # The check for current_user.is_authenticated should be done carefully regarding context.
    # After logout_user() is called, subsequent requests in the same client context should reflect this.
    status_response = logged_in_client.get(url_for('auth.status'))
    assert status_response.get_json()['authenticated'] is False


# --- Auth Status Tests (/auth/status) ---
def test_auth_status_logged_out(client):
    response = client.get(url_for('auth.status'))
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data == {"authenticated": False}

def test_auth_status_logged_in(logged_in_client, test_user, database, app): 
    fetched_test_user = database.session.get(User, test_user.id) 
    response = logged_in_client.get(url_for('auth.status'))
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["authenticated"] is True
    assert json_data["user"]["email"] == fetched_test_user.email
    assert json_data["user"]["username"] == fetched_test_user.username
    assert json_data["user"]["profile_pic"] == fetched_test_user.profile_pic
    
    # Removed redundant 'with logged_in_client:'
    logged_in_client.get('/') 
    assert current_user.is_authenticated
    assert current_user.id == fetched_test_user.id

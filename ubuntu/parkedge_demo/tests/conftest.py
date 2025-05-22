import os
import sys
import tempfile
import pytest
from flask import Flask
from flask_login import LoginManager

# Add the project root to the Python path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app as main_app
from src.models import db as _db # alias to avoid conflict with pytest fixture

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    main_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test_secret_key",
        "LOGIN_DISABLED": False,
        "GOOGLE_CLIENT_ID": "test_google_client_id",
        "GOOGLE_CLIENT_SECRET": "test_google_client_secret",
        "GOOGLE_REDIRECT_URI": "http://localhost/auth/login/google/authorized",
        "SERVER_NAME": "localhost.test" # Added to ensure url_for works correctly in all contexts
    })

    with main_app.app_context():
        _db.create_all()

    yield main_app

    with main_app.app_context():
        _db.session.remove()
        _db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def database(app): # Renamed from 'db' to 'database'
    """
    Function-scoped database fixture.
    Ensures the database is clean for each test function.
    """
    with app.app_context():
        _db.create_all()   # Recreate all tables
    yield _db # Yield the actual _db instance used by the app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def test_user(database): # Depends on 'database' fixture
    from src.models.user import User
    user = User(username="testuser", email="test@example.com", google_id="testgoogleid123")
    database.session.add(user)
    database.session.commit()
    return database.session.get(User, user.id)

@pytest.fixture
def test_space(database, test_user): # Depends on 'database' fixture
    from src.models.space import ParkingSpace
    space = ParkingSpace(
        address="123 Test St, Test City",
        latitude=34.0522,
        longitude=-118.2437,
        price="$10/hr"
    )
    database.session.add(space)
    database.session.commit()
    return database.session.get(ParkingSpace, space.id)

@pytest.fixture
def logged_in_client(client, test_user, app, database): # Added 'database' dependency
    """A test client where test_user is logged in."""
    with client:
        with app.test_request_context(): # Ensure a request context for login_user
            from flask_login import login_user
            from src.models.user import User
            # Fetch user from the session provided by the 'database' fixture
            user_to_login = database.session.get(User, test_user.id) 
            if user_to_login:
                login_user(user_to_login)
            else:
                raise ValueError(f"User with id {test_user.id} not found for login_user in test fixture.")
        yield client
        with app.test_request_context(): # Ensure a request context for logout_user
            from flask_login import logout_user
            logout_user()

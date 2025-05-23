import os
import sys
import tempfile
import pytest
import shutil # Added for directory cleanup
from flask import Flask
from flask_login import LoginManager

# Add the project root to the Python path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app as main_app
from src.models import db as _db # alias to avoid conflict with pytest fixture
# Import the UPLOAD_FOLDER from the source to be patched, if needed for initial value, but we'll override.
# from src.routes.spaces import UPLOAD_FOLDER as APP_UPLOAD_FOLDER 

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Define test upload folder path relative to this conftest.py file
    # This ensures it's within the tests directory structure.
    test_upload_base_dir = os.path.join(os.path.dirname(__file__), 'test_uploads_session')
    test_specific_upload_folder = os.path.join(test_upload_base_dir, 'parking_images')

    main_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test_secret_key",
        "LOGIN_DISABLED": False,
        "GOOGLE_CLIENT_ID": "test_google_client_id",
        "GOOGLE_CLIENT_SECRET": "test_google_client_secret",
        "GOOGLE_REDIRECT_URI": "http://localhost/auth/login/google/authorized",
        "SERVER_NAME": "localhost.test",
        "UPLOAD_FOLDER": test_specific_upload_folder # Configure app with test upload folder
    })

    # Create the test upload directory structure if it doesn't exist
    # This is for the session; individual tests might clear sub-folders.
    if not os.path.exists(test_specific_upload_folder):
        os.makedirs(test_specific_upload_folder)

    with main_app.app_context():
        _db.create_all()

    yield main_app

    with main_app.app_context():
        _db.session.remove()
        _db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)
    
    # Clean up the session-wide test upload directory
    if os.path.exists(test_upload_base_dir):
        shutil.rmtree(test_upload_base_dir)

@pytest.fixture(scope='function')
def client(app, monkeypatch): # Added monkeypatch
    """A test client for the app, with UPLOAD_FOLDER patched for routes."""
    
    # Get the test upload folder path from app config (set in app fixture)
    TEST_UPLOAD_PATH = app.config['UPLOAD_FOLDER']
    
    # Ensure the specific test upload directory (e.g., .../parking_images) exists before each test.
    # The base 'test_uploads_session' is created/deleted by the app fixture.
    if not os.path.exists(TEST_UPLOAD_PATH):
        os.makedirs(TEST_UPLOAD_PATH)

    # Monkeypatch the UPLOAD_FOLDER constant in the src.routes.spaces module
    # This is critical if the route handlers in spaces.py directly use this module-level constant.
    monkeypatch.setattr('src.routes.spaces.UPLOAD_FOLDER', TEST_UPLOAD_PATH)
    # The os.makedirs(UPLOAD_FOLDER, exist_ok=True) in spaces.py will now use this patched path.

    test_client_instance = app.test_client()
    yield test_client_instance

    # Clean up contents of the test upload folder after each test function
    # This prevents files from one test affecting another.
    if os.path.exists(TEST_UPLOAD_PATH):
        for filename in os.listdir(TEST_UPLOAD_PATH):
            file_path = os.path.join(TEST_UPLOAD_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path} during test cleanup. Reason: {e}')


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

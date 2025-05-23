import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_login import LoginManager
from src.models import db # Correctly import db
from src.models.user import User # Import the User model

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT_parkedge'

# Configure SQLite database
# The database file will be created in the 'src' directory, next to main.py
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'parkedge.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    return db.session.get(User, int(user_id))

# Import models here to ensure they are registered with SQLAlchemy before create_all
# Import User is already above, ParkingSpace and Review will be implicitly known via models/__init__.py
# when db.create_all() is called.
from src.models.space import ParkingSpace 
from src.models.review import Review # Ensure Review is imported if not covered by __all__ in models

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Import and register blueprints
from src.routes.spaces import spaces_bp
from src.routes.auth import auth_bp 
from src.routes.reviews import reviews_bp
from src.routes.booking_routes import bookings_bp # Added this line
app.register_blueprint(spaces_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/auth') 
app.register_blueprint(reviews_bp, url_prefix='/api') 
app.register_blueprint(bookings_bp) # Added this line, url_prefix is in the blueprint itself

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        map_view_path = os.path.join(static_folder_path, 'map_view.html')
        if os.path.exists(map_view_path):
            return send_from_directory(static_folder_path, 'map_view.html')
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "map_view.html or index.html not found in static folder", 404

@app.route('/uploads/parking_images/<path:filename>')
def serve_parking_image(filename):
    # Construct the absolute path to the directory where images are stored.
    # __file__ is the path to the current file (main.py)
    # os.path.dirname(__file__) gives the directory of main.py (src/)
    # Then join with 'uploads' and 'parking_images'
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'parking_images')
    return send_from_directory(upload_dir, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

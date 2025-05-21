import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from src.models import db

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT_parkedge'

# Configure SQLite database
# The database file will be created in the 'src' directory, next to main.py
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'parkedge.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Import models here to ensure they are registered with SQLAlchemy before create_all
from src.models.space import ParkingSpace

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Import and register blueprints
from src.routes.spaces import spaces_bp
app.register_blueprint(spaces_bp, url_prefix='/api')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    # Serve specific file if it exists (e.g., list_space.html, map_view.html, style.css)
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        # Default to map_view.html as the main page
        map_view_path = os.path.join(static_folder_path, 'map_view.html')
        if os.path.exists(map_view_path):
            return send_from_directory(static_folder_path, 'map_view.html')
        else:
            # Fallback to index.html if map_view.html is not created yet (though map_view is preferred)
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "map_view.html or index.html not found in static folder", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


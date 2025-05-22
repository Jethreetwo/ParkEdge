from flask import Blueprint, jsonify
from flask_login import login_required, current_user
# Assuming db is in src.models, and Booking model is also there.
# Adjust import if your db instance is elsewhere, e.g., from src import db
from src.models import db 
from src.models.booking import Booking # Import the Booking model

# Define a new Blueprint for bookings
bookings_bp = Blueprint('bookings_bp', __name__, url_prefix='/api/bookings')

@bookings_bp.route('/me', methods=['GET'])
@login_required
def get_my_bookings():
    '''
    Retrieves all bookings made by the currently logged-in user.
    '''
    # The 'bookings' backref from the Booking model (lazy='dynamic')
    # gives a query object, so we use .all() or further filtering.
    # Ordering by booking_time descending to get newest first.
    my_bookings_query = current_user.bookings.order_by(Booking.booking_time.desc())
    my_bookings = my_bookings_query.all()
    
    if not my_bookings:
        return jsonify([]), 200 # Return empty list if no bookings found
    
    return jsonify([booking.to_dict() for booking in my_bookings]), 200

# Potential future endpoints for bookings:
# POST /api/bookings (to create a booking - this is currently in space_routes.py as /api/spaces/<id>/book)
# GET /api/bookings/<booking_id> (to get a specific booking)
# PUT /api/bookings/<booking_id> (to update/cancel a booking)

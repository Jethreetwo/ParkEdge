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

from datetime import datetime # Added import

@bookings_bp.route('/<int:booking_id>/end', methods=['POST'])
@login_required
def end_booking(booking_id):
    """
    Allows a user to end their active booking.
    """
    booking = Booking.query.get_or_404(booking_id)

    # Authorization Check: Ensure the current user owns this booking
    if booking.user_id != current_user.id:
        return jsonify({"error": "Forbidden. You do not own this booking."}), 403

    # Status Check: Ensure the booking is in a state that can be ended
    # For now, assuming 'confirmed' bookings are active until explicitly ended or their end_time passes.
    # A more complex system might have an 'active' status.
    if booking.status not in ['confirmed', 'active']: # 'active' can be used if you have such a state
        return jsonify({"error": f"Booking is already {booking.status} and cannot be ended."}), 400

    # Update Booking details
    booking.status = 'ended'
    # Update end_time to now, as the user is ending it prematurely or right on time.
    # This overrides the originally calculated end_time if it was for a future point.
    booking.end_time = datetime.utcnow() 

    # Update ParkingSpace status (simplified for now)
    if booking.space:
        # The booking.space.is_booked flag is no longer directly set here.
        # Availability is dynamically determined by ParkingSpace.to_dict()
        pass # No direct change to booking.space.is_booked
    
    try:
        db.session.commit()
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error ending booking: {e}") # For server logs
        return jsonify({"error": "Failed to end booking due to a server error."}), 500

# Potential future endpoints for bookings:
# POST /api/bookings (to create a booking - this is currently in space_routes.py as /api/spaces/<id>/book)
# GET /api/bookings/<booking_id> (to get a specific booking)
# PUT /api/bookings/<booking_id> (to update/cancel a booking)

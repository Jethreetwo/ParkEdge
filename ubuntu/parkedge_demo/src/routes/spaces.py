from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from src.models import db
from src.models.space import ParkingSpace
from src.models.booking import Booking # Import the Booking model

spaces_bp = Blueprint("spaces", __name__)

@spaces_bp.route("/spaces", methods=["POST"])
@login_required
def create_space():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    address = data.get("address")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    price = data.get("price")

    if not all([address, latitude is not None, longitude is not None, price]):
        return jsonify({"error": "Missing required fields (address, latitude, longitude, price)"}), 400

    try:
        # Attempt to convert latitude and longitude to float
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({"error": "Latitude and longitude must be valid numbers"}), 400

    new_space = ParkingSpace(
        address=address,
        latitude=latitude,
        longitude=longitude,
        price=str(price), # Ensure price is stored as string as per model
        owner_id=current_user.id # Set the owner_id
    )
    db.session.add(new_space)
    db.session.commit()
    return jsonify(new_space.to_dict()), 201

@spaces_bp.route("/spaces", methods=["GET"])
def get_spaces():
    spaces = ParkingSpace.query.filter_by(is_booked=False).all()
    return jsonify([space.to_dict() for space in spaces]), 200

@spaces_bp.route("/spaces/<int:space_id>/book", methods=["POST"])
@login_required
def book_space(space_id):
    # Use db.session.get for SQLAlchemy 2.0 compatibility if preferred,
    # or keep ParkingSpace.query.get if using older versions or for consistency.
    # Assuming ParkingSpace.query.get is fine based on existing code.
    space = ParkingSpace.query.get(space_id) 
    if not space:
        return jsonify({"error": "Parking space not found"}), 404
    
    if space.is_booked: # This check might be enhanced later by looking at active bookings
        return jsonify({"error": "Parking space is already booked"}), 409 # 409 Conflict is often better for "already exists"
    
    # Prevent users from booking their own spaces
    # Ensure space.owner_id is available (added in a previous subtask)
    if hasattr(space, 'owner_id') and space.owner_id == current_user.id:
        return jsonify({"error": "You cannot book your own parking space"}), 403 # 403 Forbidden

    # Create a new booking record
    new_booking = Booking(
        user_id=current_user.id,
        space_id=space.id,
        status='confirmed' 
        # booking_time defaults to now() via model default
        # price_at_booking could be added if needed: price_at_booking=space.price
    )
    db.session.add(new_booking)
    
    # Keep the original is_booked logic for now.
    # This flag on the space might be useful for a quick "is available" check on the map,
    # while the Booking table holds detailed history and future/active bookings.
    space.is_booked = True 
    
    db.session.commit() # Commit both the new booking and the space update
    
    # Return the space details, or perhaps the booking details, or both
    # For now, returning space details as per original function
    return jsonify(space.to_dict()), 200

@spaces_bp.route('/me/spaces', methods=['GET'])
@login_required
def get_my_listed_spaces():
    '''
    Retrieves all parking spaces listed by the currently logged-in user.
    '''
    # The 'owned_spaces' backref from the ParkingSpace model (lazy='dynamic')
    # gives a query object, so we use .all()
    my_spaces = current_user.owned_spaces.all() 
    
    if not my_spaces:
        return jsonify([]), 200 # Return empty list if no spaces found
    
    return jsonify([space.to_dict() for space in my_spaces]), 200


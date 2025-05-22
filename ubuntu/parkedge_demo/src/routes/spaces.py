import requests # Add this
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

    # Update required fields for price
    required_fields = ['address', 'price_amount', 'price_unit'] 
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate price_amount
    try:
        price_amount = float(data['price_amount'])
        if price_amount <= 0:
            raise ValueError("Price amount must be positive.")
    except ValueError as e:
        return jsonify({"error": f"Invalid price_amount: {e}"}), 400

    # Validate price_unit
    price_unit = data['price_unit']
    allowed_units = ['hour', 'day'] # Define allowed units
    if price_unit not in allowed_units:
        return jsonify({"error": f"Invalid price_unit. Allowed units are: {', '.join(allowed_units)}"}), 400
    
    address = data['address']
    image_url = data.get('image_url') # Optional

    # Geocoding
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(address)}&format=json&limit=1&addressdetails=1"
    headers = {
        'User-Agent': 'ParkEdge Demo Application/1.0' # Essential for Nominatim
    }
    
    latitude = None
    longitude = None

    try:
        response = requests.get(geocode_url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status() # Raise an exception for HTTP errors (4XX, 5XX)
        results = response.json()
        
        if results and isinstance(results, list) and len(results) > 0:
            selected_result = results[0] # Default to first result
            # Optional: Heuristic to prefer more specific results if multiple are returned
            # for res_detail_check in results:
            #     if res_detail_check.get('address', {}).get('road'):
            #         selected_result = res_detail_check
            #         break
            
            latitude = selected_result.get('lat')
            longitude = selected_result.get('lon')

            if not latitude or not longitude:
                raise ValueError("Latitude or Longitude not found in geocoding response.")
            
            latitude = float(latitude) # Convert to float, as Nominatim returns strings
            longitude = float(longitude)

        else:
            return jsonify({"error": "Could not geocode address. No results found."}), 400
    except requests.exceptions.RequestException as e:
        print(f"Geocoding request failed: {e}") 
        return jsonify({"error": "Geocoding service request failed. Please try again later."}), 503
    except (ValueError, KeyError) as e:
        print(f"Error processing geocoding response: {e}")
        return jsonify({"error": "Error processing geocoding result. Ensure address is specific."}), 400

    new_space = ParkingSpace(
        address=address, # Store the original address provided by user
        latitude=latitude,
        longitude=longitude,
        price_amount=price_amount, # Use validated price_amount
        price_unit=price_unit,     # Use validated price_unit
        owner_id=current_user.id,
        image_url=image_url,
        is_booked=False # Default for new space
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

    # === New check for concurrent bookings ===
    # For SQLAlchemy 2.0 style, you might use:
    # active_booking_count = db.session.query(db.func.count(Booking.id)).filter_by(user_id=current_user.id, status='confirmed').scalar_one_or_none() or 0
    # Using filter_by().count() for consistency with provided snippet.
    active_booking_count = Booking.query.filter_by(user_id=current_user.id, status='confirmed').count()
    MAX_CONCURRENT_BOOKINGS = 3
    if active_booking_count >= MAX_CONCURRENT_BOOKINGS:
        return jsonify({"error": f"You have reached the maximum limit of {MAX_CONCURRENT_BOOKINGS} active bookings."}), 403 # Forbidden
    # === End of new check ===
    
    # Prevent users from booking their own spaces
    # Ensure space.owner_id is available (added in a previous subtask)
    if hasattr(space, 'owner_id') and space.owner_id == current_user.id:
        return jsonify({"error": "You cannot book your own parking space"}), 403 # 403 Forbidden

    if space.is_booked: # This check might be enhanced later by looking at active bookings
        return jsonify({"error": "Parking space is already booked"}), 409 # 409 Conflict is often better for "already exists"
    
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


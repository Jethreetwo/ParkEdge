import requests
from flask import Blueprint, request, jsonify, current_app # Added current_app for logger access
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import traceback # Added for detailed error logging
from datetime import datetime, timedelta 
from src.models import db
from src.models.space import ParkingSpace
from src.models.booking import Booking 
from src.models.image import ParkingSpaceImage 

spaces_bp = Blueprint("spaces", __name__)

# Define the upload folder path
UPLOAD_FOLDER = 'ubuntu/parkedge_demo/src/uploads/parking_images'
# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@spaces_bp.route("/spaces", methods=["POST"])
@login_required
def create_space():
    data = request.form # Use request.form for form data
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    required_fields = ['address', 'price_amount', 'price_unit']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        price_amount = float(data['price_amount'])
        if price_amount <= 0:
            raise ValueError("Price amount must be positive.")
    except ValueError as e:
        return jsonify({"error": f"Invalid price_amount: {e}"}), 400

    price_unit = data['price_unit']
    allowed_units = ['hour', 'day']
    if price_unit not in allowed_units:
        return jsonify({"error": f"Invalid price_unit. Allowed units are: {', '.join(allowed_units)}"}), 400
    
    address = data['address']

    # Geocoding
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(address)}&format=json&limit=1&addressdetails=1"
    headers = {
        'User-Agent': 'ParkEdge Demo Application/1.0' # Essential for Nominatim
    }
    
    latitude = None
    longitude = None

    try:
        response = requests.get(geocode_url, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        if results and isinstance(results, list) and len(results) > 0:
            selected_result = results[0]
            latitude = selected_result.get('lat')
            longitude = selected_result.get('lon')

            if not latitude or not longitude:
                raise ValueError("Latitude or Longitude not found in geocoding response.")
            
            latitude = float(latitude)
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
        address=address,
        latitude=latitude,
        longitude=longitude,
        price_amount=price_amount,
        price_unit=price_unit,
        owner_id=current_user.id,
        is_booked=False # Legacy field, actual status determined by ParkingSpace.to_dict()
    )

    # Process images and prepare ParkingSpaceImage objects
    processed_image_objects = [] # Renamed for clarity as per example
    saved_filenames_for_cleanup = [] # Keep track of filenames actually saved to disk

    files = request.files.getlist('images')
    for index, file_storage in enumerate(files):
        if file_storage and file_storage.filename:
            filename = secure_filename(file_storage.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                file_storage.save(filepath)
                saved_filenames_for_cleanup.append(filename) # Add to list for potential cleanup
            except Exception as e:
                # Log error saving file and decide if to continue or abort
                # Using current_app.logger if Flask app logger is configured
                current_app.logger.error(f"Error saving uploaded file {filename}: {e}", exc_info=True)
                # For now, skipping this file as per original logic, but this might hide issues.
                # Consider returning an error to the user if a file fails to save.
                continue 

            caption = data.get(f'caption_{index}')
            
            image_record = ParkingSpaceImage(
                image_filename=filename, 
                caption=caption
                # space_id is not set here; will be handled by relationship cascade
            )
            processed_image_objects.append(image_record)

    # Associate image objects with the new_space instance
    if processed_image_objects:
        new_space.images.extend(processed_image_objects)

    # Add new_space to the session AFTER images have been associated.
    # SQLAlchemy's cascade settings (e.g., "all, delete-orphan" on the relationship)
    # should handle adding associated ParkingSpaceImage objects to the session as well.
    db.session.add(new_space)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Clean up only successfully saved files if commit fails
        for fname in saved_filenames_for_cleanup:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, fname))
            except OSError:
                # Log this error too, but proceed with error response
                current_app.logger.error(f"Error cleaning up file {fname} after db commit failure.", exc_info=True)
                pass 
        
        # Enhanced error logging
        current_app.logger.error(f"DATABASE COMMIT ERROR in create_space: {str(e)}", exc_info=True)
        traceback.print_exc() # Also print stack trace to console/stderr for dev visibility

        return jsonify({"error": "Failed to create parking space due to a database error."}), 500
        
    return jsonify(new_space.to_dict()), 201

@spaces_bp.route("/spaces", methods=["GET"])
def get_spaces():
    spaces = ParkingSpace.query.filter_by(is_booked=False).all()
    return jsonify([space.to_dict() for space in spaces]), 200

@spaces_bp.route("/spaces/<int:space_id>/book", methods=["POST"])
@login_required
def book_space(space_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input. JSON data expected."}), 400

    duration = data.get('duration')
    duration_unit = data.get('duration_unit') # Expected 'hours' or 'days'

    if not isinstance(duration, (int, float)) or duration <= 0:
        return jsonify({"error": "Invalid duration. Must be a positive number."}), 400
    
    allowed_duration_units = ['hours', 'days']
    if duration_unit not in allowed_duration_units:
        return jsonify({"error": f"Invalid duration_unit. Allowed units are: {', '.join(allowed_duration_units)}"}), 400

    space = ParkingSpace.query.get(space_id) 
    if not space:
        return jsonify({"error": "Parking space not found"}), 404

    # Concurrent bookings check (existing logic)
    active_booking_count = Booking.query.filter_by(user_id=current_user.id, status='confirmed').count()
    MAX_CONCURRENT_BOOKINGS = 3 # This could be a config value
    if active_booking_count >= MAX_CONCURRENT_BOOKINGS:
        return jsonify({"error": f"You have reached the maximum limit of {MAX_CONCURRENT_BOOKINGS} active bookings."}), 403
    
    # Prevent booking own space (existing logic)
    if hasattr(space, 'owner_id') and space.owner_id == current_user.id:
        return jsonify({"error": "You cannot book your own parking space"}), 403

    # Availability check (simple version, to be enhanced for time slots)
    if space.is_booked: 
        return jsonify({"error": "Parking space is already marked as booked (simple check)"}), 409

    # Calculate start_time, end_time, total_price
    start_time = datetime.utcnow() # This will be set as booking_time in the model

    if duration_unit == 'hours':
        end_time = start_time + timedelta(hours=duration)
    elif duration_unit == 'days':
        end_time = start_time + timedelta(days=duration)
    else:
        # This case should be caught by earlier validation, but defensive coding
        return jsonify({"error": "Internal error: Unhandled duration unit."}), 500

    # Price calculation (simplified: assumes duration_unit matches space.price_unit or is directly convertible)
    # A more robust solution would handle conversions or disallow incompatible units.
    calculated_price = 0
    if space.price_unit == 'hour' and duration_unit == 'hours':
        calculated_price = space.price_amount * duration
    elif space.price_unit == 'day' and duration_unit == 'days':
        calculated_price = space.price_amount * duration
    elif space.price_unit == 'day' and duration_unit == 'hours':
        # Example: Convert daily price to hourly for calculation if duration is in hours.
        # This assumes a 24-hour day for proration.
        # This logic might need refinement based on business rules (e.g., minimum 1 day charge).
        calculated_price = (space.price_amount / 24) * duration
    elif space.price_unit == 'hour' and duration_unit == 'days':
        # Example: If space is priced per hour, but booking is for days.
        # Convert days to hours for calculation.
        calculated_price = space.price_amount * (duration * 24)
    else:
        # This combination should ideally be validated or handled more gracefully.
        # For now, returning an error if units are mismatched in a way not handled above.
        return jsonify({"error": f"Price unit mismatch or unsupported calculation: space priced per {space.price_unit}, booking requested in {duration_unit}."}), 400
    
    if space.price_amount is None: # Should not happen if model validation is correct
        return jsonify({"error": "Space price not set."}), 500

    new_booking = Booking(
        user_id=current_user.id,
        space_id=space.id,
        booking_time=start_time, # Explicitly set, though model has default for creation time
        end_time=end_time,
        calculated_price=round(calculated_price, 2), # Round to 2 decimal places
        status='confirmed' 
    )
    db.session.add(new_booking)
    
    # The space.is_booked flag is no longer directly set here.
    # Availability is dynamically determined by ParkingSpace.to_dict()
    
    db.session.commit() 
    
    return jsonify(new_booking.to_dict()), 200

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


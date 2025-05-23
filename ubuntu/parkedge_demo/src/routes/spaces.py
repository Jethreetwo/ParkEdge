import requests
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from src.models import db
from src.models.space import ParkingSpace
from src.models.booking import Booking # Import the Booking model
from src.models.image import ParkingSpaceImage # Import the ParkingSpaceImage model

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
        is_booked=False
    )
    db.session.add(new_space)
    # Commit here to get new_space.id for ParkingSpaceImage instances
    # Or add all to session and commit once, SQLAlchemy handles order if relationships are set
    # For simplicity and clarity, let's add space first, then images, then commit.

    images = request.files.getlist('images')
    for index, file_storage in enumerate(images):
        if file_storage and file_storage.filename:
            filename = secure_filename(file_storage.filename)
            # Consider adding a UUID or timestamp to filename to ensure uniqueness
            # For now, using the direct secure_filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file_storage.save(filepath)
            
            caption = data.get(f'caption_{index}') # Get corresponding caption

            image_record = ParkingSpaceImage(
                space_id=new_space.id, # This requires new_space to have an ID.
                                       # If not committed yet, need to handle differently or commit new_space first.
                                       # A better way: associate objects via relationship before commit
                image_filename=filename,
                caption=caption
            )
            # Instead of setting space_id directly, append to relationship:
            # new_space.images.append(image_record) # Assuming 'images' is the backref name
            # And then add image_record to session.
            # However, the current ParkingSpaceImage model sets space_id directly
            # and has a backref that would populate space.images.
            # To make space_id available, we can flush the session.
            db.session.add(image_record)

    # If new_space was not committed earlier, all objects (new_space and image_records)
    # are added to the session and a single commit will persist them.
    # If new_space.images relationship was used, this would be cleaner.
    # Given the current structure, and to ensure new_space.id is populated before
    # image_record is created (if not using relationship append),
    # we might need to flush or commit new_space earlier.
    
    # Let's adjust to add new_space, then add all images, then commit once.
    # SQLAlchemy should handle the order if ParkingSpaceImage.space relationship is correctly defined.
    # The `space = relationship('ParkingSpace', backref=db.backref('images', ...))` in image.py
    # and `space_id = db.Column(Integer, ForeignKey('parking_space.id'), ...)` should allow this.
    # We need to associate the image with the space object itself.

    # Revised approach for associating images:
    # Create new_space (don't add to session yet or don't commit)
    # Create ParkingSpaceImage objects, and append them to new_space.images (the relationship attribute)
    # Then add new_space to session (which cascades to related images if configured)
    # Then commit.

    # Re-adjusting the flow for image handling with relationships:
    # (Assuming 'images' is the relationship attribute on ParkingSpace model,
    #  which is established by the backref in ParkingSpaceImage model)

    # Clear previous image processing for this re-adjustment
    # (The above loop for images needs to be part of the new flow)
    
    # Corrected flow:
    # 1. Create ParkingSpace instance (new_space)
    # 2. For each uploaded image:
    #    a. Save file
    #    b. Create ParkingSpaceImage instance (image_record)
    #    c. Set image_record.image_filename, image_record.caption
    #    d. Append image_record to new_space.images (the collection)
    # 3. Add new_space to db.session (this should also prepare related images for commit if cascade is set)
    # 4. db.session.commit()

    # Let's rewrite the object creation and commit part
    # Previous new_space and db.session.add(new_space) are fine.
    # The loop for images needs to correctly associate with new_space.

    # The ParkingSpaceImage model has:
    # space = db.relationship('ParkingSpace', backref=db.backref('images', lazy='dynamic', cascade='all, delete-orphan'))
    # This means new_space will have an 'images' attribute.

    processed_images = []
    files = request.files.getlist('images') # getlist for multiple files
    for index, file_storage in enumerate(files):
        if file_storage and file_storage.filename:
            filename = secure_filename(file_storage.filename)
            # To make filenames more unique, prepend with space ID and index or a UUID
            # For now, keeping it simple as per initial plan.
            # unique_filename = f"{new_space.id}_{index}_{filename}" # Requires new_space.id
            # This implies new_space needs to be flushed to get an ID.
            
            # Let's save file first, then create image record.
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                file_storage.save(filepath)
            except Exception as e:
                # Handle file save error if necessary
                print(f"Error saving file {filename}: {e}")
                # Potentially skip this image or return an error
                continue 

            caption = data.get(f'caption_{index}')
            
            image_record = ParkingSpaceImage(
                image_filename=filename, 
                caption=caption
                # space_id will be set by appending to new_space.images
            )
            processed_images.append(image_record)

    if processed_images:
        new_space.images.extend(processed_images) # Use extend for a list of images

    # Now new_space is created, and image_records are associated via new_space.images
    # Add new_space to the session. If cascade is set up correctly in the model
    # (e.g., cascade="all, delete-orphan" on the relationship), 
    # the associated ParkingSpaceImage objects will also be added/managed.
    # db.session.add(new_space) was already called.

    try:
        db.session.commit()
    except Exception as e:
        # If commit fails, try to rollback changes to avoid partial data save
        db.session.rollback()
        # Optionally, delete saved files if commit fails
        for record in processed_images:
            if record.image_filename:
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, record.image_filename))
                except OSError:
                    pass # Ignore if file cannot be removed
        return jsonify({"error": "Failed to create parking space and save images. Database error."}), 500
        
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


from flask import Blueprint, request, jsonify
from src.models import db
from src.models.space import ParkingSpace

spaces_bp = Blueprint("spaces", __name__)

@spaces_bp.route("/spaces", methods=["POST"])
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
        price=str(price) # Ensure price is stored as string as per model
    )
    db.session.add(new_space)
    db.session.commit()
    return jsonify(new_space.to_dict()), 201

@spaces_bp.route("/spaces", methods=["GET"])
def get_spaces():
    spaces = ParkingSpace.query.filter_by(is_booked=False).all()
    return jsonify([space.to_dict() for space in spaces]), 200

@spaces_bp.route("/spaces/<int:space_id>/book", methods=["POST"])
def book_space(space_id):
    space = ParkingSpace.query.get(space_id)
    if not space:
        return jsonify({"error": "Parking space not found"}), 404
    
    if space.is_booked:
        return jsonify({"error": "Parking space already booked"}), 400

    space.is_booked = True
    db.session.commit()
    return jsonify(space.to_dict()), 200


from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user # Added current_user and login_required
from src.models.user import User, db

user_bp = Blueprint('user', __name__) # Existing blueprint, no url_prefix here

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    
    data = request.json
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204

@user_bp.route('/me/profile', methods=['PUT']) # New route
@login_required
def update_my_profile(): # New function name
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, expecting JSON."}), 400

    updated = False # Flag to check if any updates were made

    # Update payment_info if provided
    if 'payment_info' in data:
        current_user.payment_info = data['payment_info'] # Allows setting to empty string or null if sent
        updated = True
    
    # Update phone_number if provided
    if 'phone_number' in data:
        # Basic validation: ensure it's a string, or None/empty. 
        # More complex validation (e.g., regex for phone format) could be added if needed.
        phone_val = data['phone_number']
        if phone_val is None or isinstance(phone_val, str):
            current_user.phone_number = phone_val
            updated = True
        else:
            # If phone_number is provided but not a string or null, it's an error for this field
            return jsonify({"error": "Invalid type for phone_number. It should be a string or null."}), 400
    
    if not updated:
        # Optional: return an error or specific message if no valid fields were provided for update
        # For now, just returning current state if nothing was updated.
        return jsonify(current_user.to_dict()), 200


    try:
        db.session.commit()
        return jsonify(current_user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {e}") # Server-side log
        return jsonify({"error": "Failed to update profile information."}), 500

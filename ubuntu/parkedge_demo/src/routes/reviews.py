from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from src.models import db # Correctly import db
from src.models.review import Review
from src.models.space import ParkingSpace
from src.models.user import User

reviews_bp = Blueprint('reviews_bp', __name__)

# POST /spaces/<int:space_id>/reviews
@reviews_bp.route('/spaces/<int:space_id>/reviews', methods=['POST'])
@login_required
def create_review_for_space(space_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    space = db.session.get(ParkingSpace, space_id)
    if not space:
        return jsonify({"error": "Parking space not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    rating = data.get('rating')
    comment = data.get('comment')

    if rating is None:
        return jsonify({"error": "Rating is required"}), 400
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    # Updated to use SQLAlchemy 2.0 syntax
    existing_review_stmt = db.select(Review).filter_by(user_id=current_user.id, space_id=space_id)
    existing_review = db.session.execute(existing_review_stmt).scalar_one_or_none()
    if existing_review:
        return jsonify({"error": "You have already reviewed this parking space"}), 409 

    review = Review(
        user_id=current_user.id,
        space_id=space_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201

# GET /spaces/<int:space_id>/reviews
@reviews_bp.route('/spaces/<int:space_id>/reviews', methods=['GET'])
def get_reviews_for_space(space_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    space = db.session.get(ParkingSpace, space_id)
    if not space:
        return jsonify({"error": "Parking space not found"}), 404
    
    # Updated to use SQLAlchemy 2.0 syntax
    reviews_stmt = db.select(Review).filter_by(space_id=space_id).order_by(Review.timestamp.desc())
    reviews = db.session.execute(reviews_stmt).scalars().all()
    return jsonify([review.to_dict() for review in reviews]), 200

# GET /users/<int:user_id>/reviews
@reviews_bp.route('/users/<int:user_id>/reviews', methods=['GET'])
def get_reviews_by_user(user_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Updated to use SQLAlchemy 2.0 syntax
    reviews_stmt = db.select(Review).filter_by(user_id=user_id).order_by(Review.timestamp.desc())
    reviews = db.session.execute(reviews_stmt).scalars().all()
    return jsonify([review.to_dict() for review in reviews]), 200

# PUT /reviews/<int:review_id>
@reviews_bp.route('/reviews/<int:review_id>', methods=['PUT'])
@login_required
def update_review(review_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    review = db.session.get(Review, review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    if review.user_id != current_user.id:
        return jsonify({"error": "Forbidden: You can only update your own reviews"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    if 'rating' in data:
        rating = data['rating']
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
        review.rating = rating
    
    if 'comment' in data: # Allow empty string for comment
        review.comment = data.get('comment')
    
    db.session.commit()
    return jsonify(review.to_dict()), 200

# DELETE /reviews/<int:review_id>
@reviews_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def delete_review(review_id):
    # Updated to use SQLAlchemy 2.0 db.session.get
    review = db.session.get(Review, review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    if review.user_id != current_user.id:
        return jsonify({"error": "Forbidden: You can only delete your own reviews"}), 403
        
    db.session.delete(review)
    db.session.commit()
    return '', 204

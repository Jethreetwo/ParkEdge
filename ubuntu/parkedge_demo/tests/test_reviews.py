import pytest
from flask import url_for
from src.models.review import Review
from src.models.user import User 
from src.models.space import ParkingSpace 
from src.models import db as _db # Use _db to avoid conflict with database fixture

# Helper to create a review directly in DB for testing GET/PUT/DELETE
def create_review_direct(db_session, user_id, space_id, rating, comment):
    review = Review(user_id=user_id, space_id=space_id, rating=rating, comment=comment)
    db_session.add(review)
    db_session.commit()
    return review

# --- Test POST /api/spaces/<space_id>/reviews (Create Review) ---
def test_create_review_success(logged_in_client, test_user, test_space, database): 
    response = logged_in_client.post(
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 5, 'comment': 'Excellent!'}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['rating'] == 5
    assert data['comment'] == 'Excellent!'
    assert data['user_id'] == test_user.id
    assert data['space_id'] == test_space.id
    assert database.session.scalar(_db.select(_db.func.count()).select_from(Review)) == 1 

def test_create_review_not_authenticated(client, test_space, database): # Added database
    response = client.post(
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 5, 'comment': 'Attempt by unauth user'}
    )
    assert response.status_code == 302 
    assert url_for('auth.login') in response.location

def test_create_review_invalid_space_id(logged_in_client, database): # Added database
    response = logged_in_client.post(
        url_for('reviews_bp.create_review_for_space', space_id=9999), 
        json={'rating': 5, 'comment': 'Test'}
    )
    assert response.status_code == 404
    assert "Parking space not found" in response.get_data(as_text=True)

def test_create_review_invalid_rating(logged_in_client, test_space, database): # Added database
    response_low = logged_in_client.post(
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 0, 'comment': 'Too low'}
    )
    assert response_low.status_code == 400
    assert "Rating must be an integer between 1 and 5" in response_low.get_data(as_text=True)

    response_high = logged_in_client.post(
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 6, 'comment': 'Too high'}
    )
    assert response_high.status_code == 400
    assert "Rating must be an integer between 1 and 5" in response_high.get_data(as_text=True)
    
    response_missing = logged_in_client.post(
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'comment': 'Missing rating'}
    )
    assert response_missing.status_code == 400
    assert "Rating is required" in response_missing.get_data(as_text=True)

def test_create_review_duplicate(logged_in_client, test_user, test_space, database): 
    logged_in_client.post( 
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 4, 'comment': 'First review'}
    )
    response = logged_in_client.post( 
        url_for('reviews_bp.create_review_for_space', space_id=test_space.id),
        json={'rating': 3, 'comment': 'Second attempt'}
    )
    assert response.status_code == 409
    assert "You have already reviewed this parking space" in response.get_data(as_text=True)
    assert database.session.scalar(_db.select(_db.func.count()).select_from(Review)) == 1 

# --- Test GET /api/spaces/<space_id>/reviews (Get Reviews for Space) ---
def test_get_reviews_for_space_success(client, test_user, test_space, database): 
    create_review_direct(database.session, test_user.id, test_space.id, 5, "Great space!")
    create_review_direct(database.session, test_user.id, test_space.id, 4, "Good space") 

    response = client.get(url_for('reviews_bp.get_reviews_for_space', space_id=test_space.id))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['rating'] == 4 
    assert data[1]['rating'] == 5

def test_get_reviews_for_space_no_reviews(client, test_space, database): # Added database
    response = client.get(url_for('reviews_bp.get_reviews_for_space', space_id=test_space.id))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 0

def test_get_reviews_for_space_invalid_id(client, database): # Added database fixture
    response = client.get(url_for('reviews_bp.get_reviews_for_space', space_id=999))
    assert response.status_code == 404
    assert "Parking space not found" in response.get_data(as_text=True)

# --- Test GET /api/users/<user_id>/reviews (Get Reviews by User) ---
def test_get_reviews_by_user_success(client, test_user, test_space, database): 
    create_review_direct(database.session, test_user.id, test_space.id, 5, "My first review")
    
    space2 = ParkingSpace(address="456 Other St", latitude=35.0, longitude=-119.0, price="$2")
    database.session.add(space2) 
    database.session.commit() 
    create_review_direct(database.session, test_user.id, space2.id, 3, "My second review")

    response = client.get(url_for('reviews_bp.get_reviews_by_user', user_id=test_user.id))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['comment'] == "My second review" 
    assert data[1]['comment'] == "My first review"

def test_get_reviews_by_user_no_reviews(client, test_user, database): # Added database
    response = client.get(url_for('reviews_bp.get_reviews_by_user', user_id=test_user.id))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 0

def test_get_reviews_by_user_invalid_id(client, database): # Added database fixture
    response = client.get(url_for('reviews_bp.get_reviews_by_user', user_id=999))
    assert response.status_code == 404
    assert "User not found" in response.get_data(as_text=True)

# --- Test PUT /api/reviews/<review_id> (Update Review) ---
def test_update_review_success(logged_in_client, test_user, test_space, database): 
    review = create_review_direct(database.session, test_user.id, test_space.id, 4, "Initial comment")
    response = logged_in_client.put(
        url_for('reviews_bp.update_review', review_id=review.id),
        json={'rating': 5, 'comment': 'Updated comment'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['rating'] == 5
    assert data['comment'] == 'Updated comment'
    
    updated_review = database.session.get(Review, review.id) 
    assert updated_review.rating == 5
    assert updated_review.comment == "Updated comment"

def test_update_review_not_authenticated(client, test_user, test_space, database): 
    review = create_review_direct(database.session, test_user.id, test_space.id, 4, "Initial comment")
    response = client.put(
        url_for('reviews_bp.update_review', review_id=review.id),
        json={'rating': 5, 'comment': 'Updated comment'}
    )
    assert response.status_code == 302 

def test_update_review_not_author(logged_in_client, test_user, test_space, database): 
    author = User(username="author", email="author@example.com", google_id="author_google_id")
    database.session.add(author) 
    database.session.commit() 
    review = create_review_direct(database.session, author.id, test_space.id, 4, "Author's comment")

    response = logged_in_client.put(
        url_for('reviews_bp.update_review', review_id=review.id),
        json={'rating': 5, 'comment': 'Attempted update by non-author'}
    )
    assert response.status_code == 403
    assert "Forbidden: You can only update your own reviews" in response.get_data(as_text=True)

def test_update_review_invalid_review_id(logged_in_client, database): # Added database
    response = logged_in_client.put(
        url_for('reviews_bp.update_review', review_id=999),
        json={'rating': 5, 'comment': 'Test'}
    )
    assert response.status_code == 404
    assert "Review not found" in response.get_data(as_text=True)

def test_update_review_invalid_rating_value(logged_in_client, test_user, test_space, database): 
    review = create_review_direct(database.session, test_user.id, test_space.id, 4, "Initial comment")
    response = logged_in_client.put(
        url_for('reviews_bp.update_review', review_id=review.id),
        json={'rating': 0, 'comment': 'Invalid rating update'}
    )
    assert response.status_code == 400
    assert "Rating must be an integer between 1 and 5" in response.get_data(as_text=True)

# --- Test DELETE /api/reviews/<review_id> (Delete Review) ---
def test_delete_review_success(logged_in_client, test_user, test_space, database): 
    review = create_review_direct(database.session, test_user.id, test_space.id, 4, "To be deleted")
    assert database.session.scalar(_db.select(_db.func.count()).select_from(Review)) == 1 
    response = logged_in_client.delete(url_for('reviews_bp.delete_review', review_id=review.id))
    assert response.status_code == 204
    assert database.session.scalar(_db.select(_db.func.count()).select_from(Review)) == 0 

def test_delete_review_not_authenticated(client, test_user, test_space, database): 
    review = create_review_direct(database.session, test_user.id, test_space.id, 4, "To be deleted")
    response = client.delete(url_for('reviews_bp.delete_review', review_id=review.id))
    assert response.status_code == 302 

def test_delete_review_not_author(logged_in_client, test_user, test_space, database): 
    author = User(username="author2", email="author2@example.com", google_id="author_google_id2")
    database.session.add(author) 
    database.session.commit() 
    review = create_review_direct(database.session, author.id, test_space.id, 4, "Author's comment for delete")
    
    response = logged_in_client.delete(url_for('reviews_bp.delete_review', review_id=review.id))
    assert response.status_code == 403
    assert "Forbidden: You can only delete your own reviews" in response.get_data(as_text=True)
    assert database.session.scalar(_db.select(_db.func.count()).select_from(Review)) == 1 

def test_delete_review_invalid_id(logged_in_client, database): # Added database
    response = logged_in_client.delete(url_for('reviews_bp.delete_review', review_id=999))
    assert response.status_code == 404
    assert "Review not found" in response.get_data(as_text=True)

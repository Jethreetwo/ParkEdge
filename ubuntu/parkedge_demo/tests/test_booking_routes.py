import pytest
from src.models.user import User
from src.models.space import ParkingSpace
from src.models.image import ParkingSpaceImage
from src.models.booking import Booking
from datetime import datetime, timedelta

def test_get_my_bookings_with_space_details_and_images(logged_in_client, database, test_user, app):
    """
    Test retrieving user's bookings, ensuring space_details includes images.
    The logged_in_client uses the test_user fixture.
    """
    # 1. Create another user to own the space (optional, but good practice)
    space_owner = User(username="space_owner_bookings", email="owner_bookings@example.com")
    database.session.add(space_owner)
    database.session.commit()

    # 2. Create a ParkingSpace
    space = ParkingSpace(
        address="111 Booking Test Rd",
        latitude=35.0,
        longitude=-120.0,
        price_amount=50.0,
        price_unit="day",
        owner_id=space_owner.id
    )
    database.session.add(space)
    database.session.commit() # Commit to get space.id

    # 3. Add images to the ParkingSpace
    image1 = ParkingSpaceImage(
        space_id=space.id,
        image_filename="booking_img1.jpg",
        caption="Front view for booking"
    )
    image2 = ParkingSpaceImage(
        space_id=space.id,
        image_filename="booking_img2.png",
        caption="Entrance for booking"
    )
    database.session.add_all([image1, image2])
    database.session.commit()

    # 4. Create a Booking for the logged-in user (test_user)
    booking = Booking(
        user_id=test_user.id, # test_user is the one logged in by logged_in_client
        space_id=space.id,
        booking_time=datetime.utcnow() - timedelta(days=1), # A past booking
        status="confirmed"
    )
    database.session.add(booking)
    database.session.commit()

    # 5. Make a GET request to /api/bookings/me
    response = logged_in_client.get("/api/bookings/me")
    assert response.status_code == 200

    # 6. Parse the JSON response and verify
    bookings_data = response.get_json()
    assert isinstance(bookings_data, list)
    assert len(bookings_data) == 1 # Expecting one booking for the test_user

    retrieved_booking = bookings_data[0]
    assert retrieved_booking['id'] == booking.id
    assert retrieved_booking['user_id'] == test_user.id
    assert retrieved_booking['space_id'] == space.id
    assert retrieved_booking['status'] == "confirmed"

    # Verify space_details
    assert "space_details" in retrieved_booking
    space_details = retrieved_booking['space_details']
    assert space_details is not None
    assert space_details['id'] == space.id
    assert space_details['address'] == "111 Booking Test Rd"

    # Verify images within space_details
    assert "images" in space_details
    images_in_details = space_details['images']
    assert isinstance(images_in_details, list)
    assert len(images_in_details) == 2

    # Sort by filename for consistent order in assertion
    images_in_details_sorted = sorted(images_in_details, key=lambda x: x['image_filename'])
    
    expected_images_data = [
        {'image_filename': 'booking_img1.jpg', 'caption': 'Front view for booking'},
        {'image_filename': 'booking_img2.png', 'caption': 'Entrance for booking'}
    ]
    expected_images_data_sorted = sorted(expected_images_data, key=lambda x: x['image_filename'])

    assert images_in_details_sorted[0]['image_filename'] == expected_images_data_sorted[0]['image_filename']
    assert images_in_details_sorted[0]['caption'] == expected_images_data_sorted[0]['caption']
    assert images_in_details_sorted[1]['image_filename'] == expected_images_data_sorted[1]['image_filename']
    assert images_in_details_sorted[1]['caption'] == expected_images_data_sorted[1]['caption']

def test_get_my_bookings_no_bookings(logged_in_client, database, test_user):
    """Test retrieving user's bookings when they have none."""
    response = logged_in_client.get("/api/bookings/me")
    assert response.status_code == 200
    bookings_data = response.get_json()
    assert isinstance(bookings_data, list)
    assert len(bookings_data) == 0

def test_get_my_bookings_space_with_no_images(logged_in_client, database, test_user):
    """Test retrieving bookings where the booked space has no images."""
    space_owner = User(username="no_image_owner", email="no_image_owner@example.com")
    database.session.add(space_owner)
    database.session.commit()

    space_no_img = ParkingSpace(
        address="Space With No Images",
        latitude=36.0, longitude=-121.0,
        price_amount=30.0, price_unit="hour",
        owner_id=space_owner.id
    )
    database.session.add(space_no_img)
    database.session.commit()

    booking_no_img_space = Booking(
        user_id=test_user.id,
        space_id=space_no_img.id,
        status="completed"
    )
    database.session.add(booking_no_img_space)
    database.session.commit()

    response = logged_in_client.get("/api/bookings/me")
    assert response.status_code == 200
    bookings_data = response.get_json()
    assert len(bookings_data) == 1
    
    retrieved_booking = bookings_data[0]
    assert "space_details" in retrieved_booking
    space_details = retrieved_booking['space_details']
    assert space_details is not None
    assert space_details['id'] == space_no_img.id
    
    assert "images" in space_details
    assert isinstance(space_details['images'], list)
    assert len(space_details['images']) == 0

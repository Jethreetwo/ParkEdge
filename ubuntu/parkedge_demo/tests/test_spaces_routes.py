import pytest
import io
import os
from src.models.user import User
from src.models.space import ParkingSpace
from src.models.image import ParkingSpaceImage
from src.models.booking import Booking # Import Booking model

# Test creating a space successfully (no images, basic test)
def test_create_space_successfully_no_images(logged_in_client, database, test_user): # test_user is used as logged_in_user
    """Test creating a parking space successfully without any images."""
    response = logged_in_client.post("/api/spaces", data={ 
        "address": "1 Test Address, Testville",
        "price_amount": "15.0", 
        "price_unit": "day"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['address'] == "1 Test Address, Testville"
    assert data['owner_id'] == test_user.id 
    assert data['price_amount'] == 15.0
    assert data['price_unit'] == "day"
    assert "images" in data 
    assert isinstance(data["images"], list)
    assert len(data["images"]) == 0

    # Verify the space was actually saved in the database
    space = database.session.get(ParkingSpace, data['id'])
    assert space is not None
    assert space.address == "1 Test Address, Testville"
    assert space.owner_id == test_user.id
    assert space.price_amount == 15.0
    assert space.price_unit == "day"
    assert len(space.images.all()) == 0


# Tests for creating spaces with images (existing tests from previous step)
def test_create_space_with_single_image(logged_in_client, database, test_user, app):
    """Test creating a parking space with a single image and caption."""
    test_upload_folder = app.config['UPLOAD_FOLDER']
    
    image_content = b"fakeimagebytes_single"
    # When sending files with `data` in test_client.post, the file field should be a tuple
    # (BytesIO_object, filename_string)
    image_file_tuple = (io.BytesIO(image_content), 'test_single.jpg')
    
    form_data = {
        'address': "123 Image St, Photoville",
        'price_amount': "20.0",
        'price_unit': "hour",
        'images': image_file_tuple, # File field
        'caption_0': "Main view of the spot" # Caption for the first image
    }

    response = logged_in_client.post(
        "/api/spaces",
        data=form_data,
        content_type='multipart/form-data' # Essential for file uploads
    )

    assert response.status_code == 201, f"Response JSON: {response.get_json()}"
    response_data = response.get_json()
    assert response_data['address'] == "123 Image St, Photoville"
    assert response_data['owner_id'] == test_user.id
    assert "images" in response_data
    assert len(response_data["images"]) == 1
    assert response_data["images"][0]['image_filename'] == 'test_single.jpg'
    assert response_data["images"][0]['caption'] == "Main view of the spot"

    # Verify DB
    space = database.session.get(ParkingSpace, response_data['id'])
    assert space is not None
    assert len(space.images.all()) == 1
    db_image = space.images.first()
    assert db_image.image_filename == 'test_single.jpg'
    assert db_image.caption == "Main view of the spot"

    # Verify file "saved" to the test upload folder
    expected_file_path = os.path.join(test_upload_folder, 'test_single.jpg')
    assert os.path.exists(expected_file_path)
    with open(expected_file_path, 'rb') as f:
        assert f.read() == image_content

def test_create_space_with_multiple_images(logged_in_client, database, test_user, app):
    """Test creating a parking space with multiple images and captions."""
    test_upload_folder = app.config['UPLOAD_FOLDER']

    image_content1 = b"fakeimagebytes_multi1"
    image_content2 = b"fakeimagebytes_multi2"
    
    # For multiple files with the same field name 'images', pass a list of (BytesIO, filename) tuples
    form_data = {
        'address': "789 Gallery Pl, Art City",
        'price_amount': "25.50",
        'price_unit': "day",
        'images': [
            (io.BytesIO(image_content1), 'photo1.png'),
            (io.BytesIO(image_content2), 'photo2.jpeg')
        ],
        'caption_0': "Front entrance", # Caption for the first image in the list
        'caption_1': "Side alley view"  # Caption for the second image
    }

    response = logged_in_client.post(
        "/api/spaces",
        data=form_data,
        content_type='multipart/form-data'
    )

    assert response.status_code == 201, f"Response JSON: {response.get_json()}"
    response_data = response.get_json()
    assert response_data['address'] == "789 Gallery Pl, Art City"
    assert len(response_data["images"]) == 2
    
    response_images_sorted = sorted(response_data["images"], key=lambda x: x['image_filename'])
    
    assert response_images_sorted[0]['image_filename'] == 'photo1.png'
    assert response_images_sorted[0]['caption'] == "Front entrance"
    assert response_images_sorted[1]['image_filename'] == 'photo2.jpeg'
    assert response_images_sorted[1]['caption'] == "Side alley view"

    # Verify DB
    space = database.session.get(ParkingSpace, response_data['id'])
    assert space is not None
    assert len(space.images.all()) == 2
    db_images_sorted = sorted(space.images, key=lambda x: x.image_filename) # Assuming images relationship is queryable
    assert db_images_sorted[0].image_filename == 'photo1.png'
    assert db_images_sorted[0].caption == "Front entrance"
    assert db_images_sorted[1].image_filename == 'photo2.jpeg'
    assert db_images_sorted[1].caption == "Side alley view"

    # Verify files "saved"
    expected_file_path1 = os.path.join(test_upload_folder, 'photo1.png')
    assert os.path.exists(expected_file_path1)
    with open(expected_file_path1, 'rb') as f:
        assert f.read() == image_content1
        
    expected_file_path2 = os.path.join(test_upload_folder, 'photo2.jpeg')
    assert os.path.exists(expected_file_path2)
    with open(expected_file_path2, 'rb') as f:
        assert f.read() == image_content2

def test_create_space_image_upload_no_captions(logged_in_client, database, test_user, app):
    """Test creating a space with an image but no caption provided for it."""
    test_upload_folder = app.config['UPLOAD_FOLDER']
    image_content = b"image_no_caption_content"
    image_file_tuple = (io.BytesIO(image_content), 'no_caption_img.gif')

    form_data = {
        'address': "555 Silent Film St",
        'price_amount': "12.0",
        'price_unit': "hour",
        'images': image_file_tuple
        # No caption_0 intentionally
    }
    response = logged_in_client.post("/api/spaces", data=form_data, content_type='multipart/form-data')
    assert response.status_code == 201, f"Response JSON: {response.get_json()}"
    response_data = response.get_json()
    assert len(response_data["images"]) == 1
    assert response_data["images"][0]['image_filename'] == 'no_caption_img.gif'
    assert response_data["images"][0]['caption'] is None 

    space = database.session.get(ParkingSpace, response_data['id'])
    assert space is not None
    db_image = space.images.first()
    assert db_image.image_filename == 'no_caption_img.gif'
    assert db_image.caption is None

    expected_file_path = os.path.join(test_upload_folder, 'no_caption_img.gif')
    assert os.path.exists(expected_file_path)

# Test creating a space with missing required fields
def test_create_space_missing_fields(logged_in_client, database):
    response = logged_in_client.post("/api/spaces", data={}) # Empty data
    assert response.status_code == 400 
    data = response.get_json()
    assert "error" in data
    assert "Missing required field" in data["error"]

# Test creating a space with invalid price_amount (e.g., negative)
def test_create_space_invalid_price_amount(logged_in_client, database):
    response = logged_in_client.post("/api/spaces", data={ 
        "address": "123 Invalid Price St",
        "price_amount": "-5.0", 
        "price_unit": "hour"
    }) 
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Invalid price_amount" in data["error"]

# Test creating a space with invalid price_unit
def test_create_space_invalid_price_unit(logged_in_client, database):
    response = logged_in_client.post("/api/spaces", data={ 
        "address": "456 Invalid Unit Rd",
        "price_amount": "10.0",
        "price_unit": "minute" 
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Invalid price_unit" in data["error"]

# Test creating a space when not logged in
def test_create_space_not_logged_in(client, database): # Use basic client
    response = client.post("/api/spaces", data={ 
        "address": "789 Unauthorized Ave",
        "price_amount": "20.0",
        "price_unit": "day"
    })
    assert response.status_code == 401 

# Test getting all available parking spaces
def test_get_available_spaces(client, database, test_user): 
    space1 = ParkingSpace(address="10 Available St", latitude=10.0, longitude=10.0, price_amount=5.0, price_unit="hour", owner_id=test_user.id, is_booked=False)
    space2 = ParkingSpace(address="20 Booked Rd", latitude=20.0, longitude=20.0, price_amount=10.0, price_unit="day", owner_id=test_user.id, is_booked=True)
    space3 = ParkingSpace(address="30 Another Available Ave", latitude=30.0, longitude=30.0, price_amount=15.0, price_unit="hour", owner_id=test_user.id, is_booked=False)
    database.session.add_all([space1, space2, space3])
    database.session.commit()

    response = client.get("/api/spaces")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    
    available_space_addresses = {s['address'] for s in data}
    assert "10 Available St" in available_space_addresses
    assert "30 Another Available Ave" in available_space_addresses
    assert "20 Booked Rd" not in available_space_addresses
    assert len(data) == 2

# Test booking a space successfully
def test_book_space_successfully(logged_in_client, database, test_user): 
    other_user = User(username="otherowner", email="other@example.com")
    database.session.add(other_user)
    database.session.commit()

    space = ParkingSpace(
        address="Bookable Place", 
        latitude=40.0, longitude=40.0, 
        price_amount=20.0, price_unit="day", 
        owner_id=other_user.id, 
        is_booked=False
    )
    database.session.add(space)
    database.session.commit()

    response = logged_in_client.post(f"/api/spaces/{space.id}/book")
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == space.id
    assert data['is_booked'] is True 

    updated_space = database.session.get(ParkingSpace, space.id)
    assert updated_space.is_booked is True
    
    final_booking_check = Booking.query.filter_by(user_id=test_user.id, space_id=space.id).first()
    assert final_booking_check is not None
    assert final_booking_check.status == 'confirmed'
    # Booking time (start_time) should be recent, end_time and calculated_price are not set by this old test logic
    # This test would need to be updated if we strictly wanted to test the new booking fields from this endpoint call,
    # but the endpoint under test here doesn't take duration/unit, so it creates a simple booking.
    # The new tests below will cover the duration/unit aspects.

from freezegun import freeze_time # For mocking datetime.utcnow()
from datetime import datetime, timedelta

@freeze_time("2024-01-01 12:00:00 UTC")
def test_book_space_with_duration_successfully(logged_in_client, database, test_user):
    """Test booking a space successfully with duration and duration_unit."""
    # Create a space owner (can be test_user or another user)
    space_owner = User(username="space_owner_for_booking", email="bookingtestowner@example.com")
    database.session.add(space_owner)
    database.session.commit()

    # Create a space to be booked
    space = ParkingSpace(
        address="Duration Bookable Spot",
        latitude=10.0, longitude=10.0,
        price_amount=10.0, price_unit="hour", # Priced per hour
        owner_id=space_owner.id,
        is_booked=False # Legacy field, actual availability is dynamic
    )
    database.session.add(space)
    database.session.commit()

    booking_payload = {
        "duration": 2,
        "duration_unit": "hours"
    }

    response = logged_in_client.post(
        f"/api/spaces/{space.id}/book",
        json=booking_payload
    )
    assert response.status_code == 200 # Endpoint returns 200 on successful booking update
    data = response.get_json()

    expected_start_time = datetime.utcnow()
    expected_end_time = expected_start_time + timedelta(hours=2)
    expected_calculated_price = 10.0 * 2 # 10 per hour * 2 hours

    assert data["space_id"] == space.id
    assert data["user_id"] == test_user.id
    assert data["status"] == "confirmed"
    assert abs(datetime.fromisoformat(data["start_time"].replace("Z", "+00:00")) - expected_start_time) < timedelta(seconds=5) # Account for small diffs
    assert datetime.fromisoformat(data["end_time"].replace("Z", "+00:00")) == expected_end_time
    assert data["calculated_price"] == expected_calculated_price

    # Verify in DB
    booking_record = Booking.query.filter_by(id=data['id']).first()
    assert booking_record is not None
    assert booking_record.space_id == space.id
    assert booking_record.user_id == test_user.id
    assert abs(booking_record.booking_time - expected_start_time) < timedelta(seconds=5)
    assert booking_record.end_time == expected_end_time
    assert booking_record.calculated_price == expected_calculated_price
    assert booking_record.status == "confirmed"

def test_book_space_invalid_duration_inputs(logged_in_client, database, test_user):
    """Test booking a space with invalid duration or duration_unit."""
    space_owner = User(username="owner_invalid_booking", email="owner_invalid@example.com")
    database.session.add(space_owner)
    database.session.commit()
    space = ParkingSpace(address="Test Invalid Duration", latitude=1.0, longitude=1.0, price_amount=5.0, price_unit="hour", owner_id=space_owner.id)
    database.session.add(space)
    database.session.commit()

    # Missing duration
    response = logged_in_client.post(f"/api/spaces/{space.id}/book", json={"duration_unit": "hours"})
    assert response.status_code == 400
    assert "invalid duration" in response.get_json()["error"].lower()

    # Zero duration
    response = logged_in_client.post(f"/api/spaces/{space.id}/book", json={"duration": 0, "duration_unit": "hours"})
    assert response.status_code == 400
    assert "invalid duration" in response.get_json()["error"].lower()

    # Negative duration
    response = logged_in_client.post(f"/api/spaces/{space.id}/book", json={"duration": -1, "duration_unit": "hours"})
    assert response.status_code == 400
    assert "invalid duration" in response.get_json()["error"].lower()

    # Missing duration_unit
    response = logged_in_client.post(f"/api/spaces/{space.id}/book", json={"duration": 1})
    assert response.status_code == 400
    assert "invalid duration_unit" in response.get_json()["error"].lower()
    
    # Invalid duration_unit
    response = logged_in_client.post(f"/api/spaces/{space.id}/book", json={"duration": 1, "duration_unit": "minutes"})
    assert response.status_code == 400
    assert "invalid duration_unit" in response.get_json()["error"].lower()

    # Test price calculation mismatch (e.g., space priced per day, booking in hours with no direct conversion logic or vice-versa)
    # This depends on how strictly the backend handles price unit mismatches.
    # Current backend logic has some conversion, so this test needs to be specific.
    # Example: if backend only allows booking in space's price_unit
    day_space = ParkingSpace(address="Day Price Space", latitude=2.0, longitude=2.0, price_amount=50.0, price_unit="day", owner_id=space_owner.id)
    database.session.add(day_space)
    database.session.commit()
    
    # Assuming the backend logic for price calculation requires duration_unit to be compatible or explicitly handled.
    # The current backend route tries to convert: day price to hourly if duration is hours, and hour price to daily if duration is days.
    # A case that might fail or be considered "unsupported calculation" could be if this logic was stricter.
    # For now, the backend seems to try to accommodate, so a specific "mismatch error" might not trigger
    # unless the logic is very specific about not converting.
    # Let's test a case where conversion might lead to issues if not handled well, e.g. very small duration for daily price.
    response = logged_in_client.post(f"/api/spaces/{day_space.id}/book", json={"duration": 0.1, "duration_unit": "hours"}) # 0.1 hours for a daily priced space
    # If backend logic for (space.price_amount / 24) * duration results in a very small or zero price,
    # it should still be a valid booking if the duration is valid.
    # The test for "Price unit mismatch or unsupported calculation" would require a specific setup
    # that the backend cannot handle. The current backend has basic conversions.
    assert response.status_code == 200 # This should work with current conversion logic.
    # If the backend were to reject this, status would be 400.


# Test booking a space that is already booked
def test_book_space_already_booked(logged_in_client, database, test_user):
    other_user = User(username="anotherowner", email="another@example.com")
    database.session.add(other_user)
    database.session.commit()

    space = ParkingSpace(
        address="Already Booked Spot", 
        latitude=50.0, longitude=50.0, 
        price_amount=25.0, price_unit="hour",
        owner_id=other_user.id, 
        is_booked=True 
    )
    database.session.add(space)
    database.session.commit()

    response = logged_in_client.post(f"/api/spaces/{space.id}/book")
    assert response.status_code == 409 
    data = response.get_json()
    assert "error" in data
    assert "already booked" in data["error"].lower()

# Test booking a space that does not exist
def test_book_non_existent_space(logged_in_client, database):
    response = logged_in_client.post("/api/spaces/9999/book") 
    assert response.status_code == 404 
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()

# Test booking when not logged in
def test_book_space_not_logged_in(client, database, test_space): 
    response = client.post(f"/api/spaces/{test_space.id}/book")
    assert response.status_code == 401

# Test retrieving user's own listed spaces
def test_get_my_listed_spaces(logged_in_client, database, test_user):
    space1 = ParkingSpace(address="My Place 1", latitude=60.0, longitude=60.0, price_amount=10.0, price_unit="hour", owner_id=test_user.id)
    space2 = ParkingSpace(address="My Place 2", latitude=61.0, longitude=61.0, price_amount=12.0, price_unit="day", owner_id=test_user.id, is_booked=True)
    
    other_user = User(username="somebodyelse", email="else@example.com")
    database.session.add(other_user)
    database.session.commit()
    space_other = ParkingSpace(address="Not My Place", latitude=62.0, longitude=62.0, price_amount=15.0, price_unit="hour", owner_id=other_user.id)
    
    database.session.add_all([space1, space2, space_other])
    database.session.commit()

    response = logged_in_client.get("/api/me/spaces")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2 

    my_space_addresses = {s['address'] for s in data}
    assert "My Place 1" in my_space_addresses
    assert "My Place 2" in my_space_addresses
    assert "Not My Place" not in my_space_addresses

# Test retrieving user's own listed spaces when none exist
def test_get_my_listed_spaces_empty(logged_in_client, database, test_user):
    other_user = User(username="someone_else_entirely", email="entirely@example.com")
    database.session.add(other_user)
    database.session.commit()
    space_other_user = ParkingSpace(address="Another User's Spot", latitude=1.0, longitude=1.0, price_amount=5.0, price_unit="hour", owner_id=other_user.id)
    database.session.add(space_other_user)
    database.session.commit()

    response = logged_in_client.get("/api/me/spaces")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

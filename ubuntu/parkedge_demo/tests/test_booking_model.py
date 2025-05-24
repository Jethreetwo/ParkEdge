import pytest
from src.models.user import User
from src.models.space import ParkingSpace
from src.models.booking import Booking
from datetime import datetime, timedelta

def test_create_booking_with_new_fields(database, test_user):
    """Test creating a Booking instance with end_time and calculated_price."""
    # Create a dummy space owner
    space_owner = User(username="booking_space_owner", email="booking_owner@example.com")
    database.session.add(space_owner)
    database.session.commit()

    # Create a dummy space
    space = ParkingSpace(
        address="789 Booking Test St",
        latitude=34.0522,
        longitude=-118.2437,
        price_amount=20.0,
        price_unit="hour",
        owner_id=space_owner.id
    )
    database.session.add(space)
    database.session.commit()

    start_time = datetime.utcnow()
    end_time_val = start_time + timedelta(hours=2)
    calculated_price_val = 40.0

    booking = Booking(
        user_id=test_user.id,
        space_id=space.id,
        booking_time=start_time, # Serves as start_time
        end_time=end_time_val,
        calculated_price=calculated_price_val,
        status="confirmed"
    )
    database.session.add(booking)
    database.session.commit()

    retrieved_booking = database.session.get(Booking, booking.id)
    assert retrieved_booking is not None
    assert retrieved_booking.user_id == test_user.id
    assert retrieved_booking.space_id == space.id
    assert retrieved_booking.booking_time == start_time
    assert retrieved_booking.end_time == end_time_val
    assert retrieved_booking.calculated_price == calculated_price_val
    assert retrieved_booking.status == "confirmed"

def test_booking_to_dict_serialization(database, test_user):
    """Test Booking.to_dict() serializes new fields correctly."""
    space_owner = User(username="dict_owner", email="dict_owner@example.com")
    database.session.add(space_owner)
    database.session.commit()

    space = ParkingSpace(
        address="101 Dict Test Ave",
        latitude=34.0523,
        longitude=-118.2438,
        price_amount=15.0,
        price_unit="day",
        owner_id=space_owner.id
    )
    database.session.add(space)
    database.session.commit()

    start_time = datetime.utcnow()
    end_time_val = start_time + timedelta(days=1)
    calculated_price_val = 15.0

    booking = Booking(
        user_id=test_user.id,
        space_id=space.id,
        booking_time=start_time,
        end_time=end_time_val,
        calculated_price=calculated_price_val,
        status="active"
    )
    database.session.add(booking)
    database.session.commit()

    booking_dict = booking.to_dict()

    assert booking_dict['id'] == booking.id
    assert booking_dict['user_id'] == test_user.id
    assert booking_dict['space_id'] == space.id
    assert booking_dict['start_time'] == start_time.isoformat()
    assert booking_dict['end_time'] == end_time_val.isoformat()
    assert booking_dict['calculated_price'] == calculated_price_val
    assert booking_dict['status'] == "active"
    
    assert "space_details" in booking_dict # From previous steps
    assert booking_dict["space_details"] is not None
    assert booking_dict["space_details"]["id"] == space.id
    assert booking_dict["space_details"]["address"] == "101 Dict Test Ave"

    assert "user_username" in booking_dict # From previous steps
    assert booking_dict["user_username"] == test_user.username

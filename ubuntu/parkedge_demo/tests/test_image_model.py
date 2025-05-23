import pytest
from src.models.user import User
from src.models.space import ParkingSpace
from src.models.image import ParkingSpaceImage

def test_create_parking_space_image(database):
    """Test creating a ParkingSpaceImage instance and saving it."""
    user = User(username="owner", email="owner@example.com")
    database.session.add(user)
    database.session.commit()

    space = ParkingSpace(
        address="123 Main St",
        latitude=34.0522,
        longitude=-118.2437,
        price_amount=10.0,
        price_unit="hour",
        owner_id=user.id
    )
    database.session.add(space)
    database.session.commit()

    image = ParkingSpaceImage(
        space_id=space.id,
        image_filename="test_image.jpg",
        caption="A beautiful parking spot.",
        order=1
    )
    database.session.add(image)
    database.session.commit()

    retrieved_image = database.session.get(ParkingSpaceImage, image.id)
    assert retrieved_image is not None
    assert retrieved_image.image_filename == "test_image.jpg"
    assert retrieved_image.caption == "A beautiful parking spot."
    assert retrieved_image.order == 1
    assert retrieved_image.space_id == space.id

def test_parking_space_image_relationship(database):
    """Test the relationship between ParkingSpace and ParkingSpaceImage."""
    user = User(username="owner2", email="owner2@example.com")
    database.session.add(user)
    database.session.commit()

    space = ParkingSpace(
        address="456 Oak Ave",
        latitude=34.0523,
        longitude=-118.2438,
        price_amount=15.0,
        price_unit="day",
        owner_id=user.id
    )
    database.session.add(space)
    database.session.commit()

    image1 = ParkingSpaceImage(
        image_filename="oak_front.png",
        caption="Front view of Oak Ave space",
        order=1
    )
    image2 = ParkingSpaceImage(
        image_filename="oak_side.png",
        caption="Side view",
        order=2
    )
    
    # Associate images with the space using the relationship
    space.images.append(image1)
    space.images.append(image2)
    
    database.session.add(space) # Add space, images will be cascaded if configured
    database.session.add(image1) # Or add them explicitly
    database.session.add(image2)
    database.session.commit()

    retrieved_space = database.session.get(ParkingSpace, space.id)
    assert retrieved_space is not None
    assert len(retrieved_space.images.all()) == 2 # .all() because lazy='dynamic'

    # Verify images list from space.images
    filenames_from_space = sorted([img.image_filename for img in retrieved_space.images])
    assert filenames_from_space == sorted(["oak_front.png", "oak_side.png"])

    # Verify space object from image.space
    retrieved_image1 = database.session.query(ParkingSpaceImage).filter_by(image_filename="oak_front.png").first()
    assert retrieved_image1 is not None
    assert retrieved_image1.space == retrieved_space
    assert retrieved_image1.space_id == retrieved_space.id


def test_parking_space_to_dict_with_images(database):
    """Test ParkingSpace.to_dict() includes images correctly."""
    user = User(username="owner3", email="owner3@example.com")
    database.session.add(user)
    database.session.commit()

    space = ParkingSpace(
        address="789 Pine Ln",
        latitude=34.0524,
        longitude=-118.2439,
        price_amount=20.0,
        price_unit="hour",
        owner_id=user.id
    )
    database.session.add(space)
    database.session.commit() # Commit to get space.id

    img1 = ParkingSpaceImage(space_id=space.id, image_filename="pine1.jpg", caption="Pine Lane spot 1")
    img2 = ParkingSpaceImage(space_id=space.id, image_filename="pine2.jpg", caption="Pine Lane spot 2")
    
    database.session.add_all([img1, img2])
    database.session.commit()

    space_dict = space.to_dict()

    assert "images" in space_dict
    assert isinstance(space_dict["images"], list)
    assert len(space_dict["images"]) == 2
    
    # Order of images in to_dict might not be guaranteed unless explicitly ordered in query/relationship
    # For now, checking if expected data is present
    expected_images_data = [
        {'image_filename': 'pine1.jpg', 'caption': 'Pine Lane spot 1'},
        {'image_filename': 'pine2.jpg', 'caption': 'Pine Lane spot 2'}
    ]
    
    # Convert list of dicts to list of tuples of items to make it order-agnostic for assertion
    dict_images_as_tuples = sorted([tuple(sorted(d.items())) for d in space_dict["images"]])
    expected_images_as_tuples = sorted([tuple(sorted(d.items())) for d in expected_images_data])
    
    assert dict_images_as_tuples == expected_images_as_tuples

def test_parking_space_image_to_dict(database):
    """Test ParkingSpaceImage.to_dict() method."""
    user = User(username="owner4", email="owner4@example.com")
    database.session.add(user)
    database.session.commit()

    space = ParkingSpace(
        address="101 Maple Dr",
        latitude=34.0525,
        longitude=-118.2440,
        price_amount=5.0,
        price_unit="hour",
        owner_id=user.id
    )
    database.session.add(space)
    database.session.commit()

    image = ParkingSpaceImage(
        space_id=space.id,
        image_filename="maple_drive.jpg",
        caption="Maple Driveway",
        order=1
    )
    database.session.add(image)
    database.session.commit()

    image_dict = image.to_dict()

    assert image_dict['id'] == image.id
    assert image_dict['space_id'] == space.id
    assert image_dict['image_filename'] == "maple_drive.jpg"
    assert image_dict['caption'] == "Maple Driveway"
    assert image_dict['order'] == 1

def test_parking_space_to_dict_no_images(database):
    """Test ParkingSpace.to_dict() when there are no images."""
    user = User(username="owner5", email="owner5@example.com")
    database.session.add(user)
    database.session.commit()

    space = ParkingSpace(
        address="202 Birch Ct",
        latitude=34.0526,
        longitude=-118.2441,
        price_amount=25.0,
        price_unit="day",
        owner_id=user.id
    )
    database.session.add(space)
    database.session.commit()

    space_dict = space.to_dict()

    assert "images" in space_dict
    assert isinstance(space_dict["images"], list)
    assert len(space_dict["images"]) == 0

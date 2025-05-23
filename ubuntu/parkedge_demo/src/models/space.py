from . import db
from .review import Review # Import the Review model
from .user import User
from .image import ParkingSpaceImage # Import the ParkingSpaceImage model

class ParkingSpace(db.Model):
    __tablename__ = 'parking_space' # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    price_amount = db.Column(db.Float, nullable=False)
    price_unit = db.Column(db.String(10), nullable=False, default='hour') # e.g., "hour", "day"
    is_booked = db.Column(db.Boolean, default=False, nullable=False)

    owner = db.relationship('User', backref=db.backref('owned_spaces', lazy='dynamic')) # Using lazy='dynamic' for owned_spaces
    reviews = db.relationship('Review', backref='space', lazy=True)
    # The 'images' backref is automatically provided by ParkingSpaceImage model

    def to_dict(self):
        # Calculate average rating
        avg_rating = None
        if self.reviews:
            avg_rating = sum(review.rating for review in self.reviews) / len(self.reviews)
            avg_rating = round(avg_rating, 2)

        images_data = []
        if self.images: # self.images comes from the backref in ParkingSpaceImage
            images_data = [{'image_filename': img.image_filename, 'caption': img.caption} for img in self.images]

        return {
            "id": self.id,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "price_amount": self.price_amount,
            "price_unit": self.price_unit,
            "is_booked": self.is_booked,
            "owner_id": self.owner_id,
            "images": images_data, # Add images list
            "review_ids": [review.id for review in self.reviews],
            "average_rating": avg_rating
        }


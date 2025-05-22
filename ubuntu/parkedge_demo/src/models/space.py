from . import db
from .review import Review # Import the Review model

class ParkingSpace(db.Model):
    __tablename__ = 'parking_space' # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    price = db.Column(db.String(50), nullable=False) # Using String for simplicity, e.g., "$5/hr"
    is_booked = db.Column(db.Boolean, default=False, nullable=False)

    reviews = db.relationship('Review', backref='space', lazy=True)

    def to_dict(self):
        # Calculate average rating
        avg_rating = None
        if self.reviews:
            avg_rating = sum(review.rating for review in self.reviews) / len(self.reviews)
            avg_rating = round(avg_rating, 2)

        return {
            "id": self.id,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "price": self.price,
            "is_booked": self.is_booked,
            "review_ids": [review.id for review in self.reviews], # Optional: list review IDs
            "average_rating": avg_rating # Include average rating
        }


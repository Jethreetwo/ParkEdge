from . import db
from datetime import datetime
# It's good practice to import User and ParkingSpace if type hinting or specific relationships need them explicitly.
# from .user import User --- Not strictly needed for ForeignKey string definition but good for clarity
# from .space import ParkingSpace --- Same as above

class Booking(db.Model):
    __tablename__ = 'booking'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
    booking_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # status could be: 'pending', 'confirmed', 'active', 'completed', 'cancelled'
    status = db.Column(db.String(50), nullable=False, default='confirmed') 
    # Add price_at_booking if price can change and you want to record it
    # price_at_booking = db.Column(db.String(50), nullable=True) 

    # Relationships
    # The backref in User and ParkingSpace will allow access like user.bookings or space.bookings
    user = db.relationship('User', backref=db.backref('bookings', lazy='dynamic'))
    space = db.relationship('ParkingSpace', backref=db.backref('bookings', lazy='dynamic'))

    def __repr__(self):
        return f'<Booking {self.id} by User {self.user_id} for Space {self.space_id} - Status: {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'space_id': self.space_id,
            'booking_time': self.booking_time.isoformat(),
            'status': self.status,
            'user_username': self.user.username if self.user else None, # Optional: include for convenience
            'space_address': self.space.address if self.space else None # Optional: include for convenience
        }

from flask_login import UserMixin
from . import db # Use relative import for db
from .review import Review # Import the Review model

class User(db.Model, UserMixin):
    __tablename__ = 'user' # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=True) # Changed unique to False and nullable to True
    email = db.Column(db.String(120), unique=True, nullable=False)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)
    payment_info = db.Column(db.Text, nullable=True)
    phone_number = db.Column(db.String(30), nullable=True) # Max length 30 for international numbers + formatting

    reviews = db.relationship('Review', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username or self.email}>' # Display email if username is None

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'google_id': self.google_id,
            'profile_pic': self.profile_pic,
            'payment_info': self.payment_info,
            'phone_number': self.phone_number, # Add this line
            'review_ids': [review.id for review in self.reviews] 
        }

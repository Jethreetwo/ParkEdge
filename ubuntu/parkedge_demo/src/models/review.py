from . import db
from datetime import datetime

class Review(db.Model):
    __tablename__ = 'review' # Explicitly define table name

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)

    # Add check constraint for rating (1-5)
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='rating_check'),
    )

    def __repr__(self):
        return f'<Review {self.id} by User {self.user_id} for Space {self.space_id} - {self.rating} stars>'

    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'comment': self.comment,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None, # Access username via backref
            'space_id': self.space_id
        }

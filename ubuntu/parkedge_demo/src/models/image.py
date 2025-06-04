from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from . import db

class ParkingSpaceImage(db.Model):
    __tablename__ = 'parking_space_image'

    id = db.Column(Integer, primary_key=True)
    space_id = db.Column(Integer, ForeignKey('parking_space.id'), nullable=False)
    image_filename = db.Column(String(255), nullable=False)
    caption = db.Column(Text, nullable=True)
    order = db.Column(Integer, nullable=True)

    space = db.relationship('ParkingSpace', backref=db.backref('images', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<ParkingSpaceImage {self.image_filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'space_id': self.space_id,
            'image_filename': self.image_filename,
            'caption': self.caption,
            'order': self.order
        }

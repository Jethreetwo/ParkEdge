from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models here to ensure they are registered with SQLAlchemy
# and for easier access from other parts of the application.
from .user import User
from .space import ParkingSpace
from .review import Review
from .booking import Booking

__all__ = ['db', 'User', 'ParkingSpace', 'Review', 'Booking']


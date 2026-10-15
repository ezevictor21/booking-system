"""Database models for the DEZE Travel & Prayer Platform.

One table per form on the site:
    users            -> register / login
    bookings         -> booking form
    prayer_requests  -> prayer form
    contact_messages -> contact form
    payments         -> payment form (records the intent, never card details)
"""
from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
bcrypt = Bcrypt()

SERVICES = ("Pilgrimage Tour", "Travel Booking", "Prayer Retreat")


class User(db.Model):
    """A registered visitor. Passwords are stored only as bcrypt hashes."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True)
    payments = db.relationship("Payment", backref="user", lazy=True)

    def set_password(self, password):
        """Hash and store a plain-text password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """Return True if the password matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)


class Booking(db.Model):
    """A travel or retreat booking submitted from /booking."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    service = db.Column(db.String(50), nullable=False)
    travel_date = db.Column(db.Date, nullable=False)
    travel_return_date = db.Column(db.Date, nullable=True)
    travel_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.String(500))
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PrayerRequest(db.Model):
    """A prayer request submitted from /prayer."""

    __tablename__ = "prayer_requests"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    request = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    """A message submitted from /contact."""

    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    """A payment intent. The amount and payer are recorded here; the card is
    handled by an external provider (Paystack, Flutterwave, Stripe...)."""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

import secrets
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def generate_reference(prefix="ORD"):
    """Generate a short job/order reference code, e.g. ORD-7F3K9Q."""
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(secrets.choice(chars) for _ in range(6))}"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="customer", lazy=True)
    orders = db.relationship("Order", backref="customer", lazy=True)
    cart_items = db.relationship("CartItem", backref="owner", lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="author", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"


class ServiceCategory(db.Model):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default="printer")  # lucide icon name
    description = db.Column(db.String(255))

    services = db.relationship("Service", backref="category", lazy=True)


class Service(db.Model):
    """A single offering: could be a physical/print product (buy now) or
    a bookable service (photo shoot, event planning, consultation)."""

    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    short_description = db.Column(db.String(255))
    description = db.Column(db.Text)
    image = db.Column(db.String(255), default="img/placeholder-service.jpg")

    price = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(50), default="item")  # e.g. "per item", "per session", "per event"

    is_bookable = db.Column(db.Boolean, default=False)  # requires a scheduled session
    is_purchasable = db.Column(db.Boolean, default=True)  # can be added to cart directly
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="service", lazy=True)
    reviews = db.relationship("Review", backref="service", lazy=True)

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)


class Booking(db.Model):
    """A scheduled session: photo shoot, video coverage, event consultation, etc."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, default=lambda: generate_reference("BKG"))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)

    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(255))  # studio or on-site address
    event_type = db.Column(db.String(100))  # wedding, birthday, corporate, product shoot...
    notes = db.Column(db.Text)

    status = db.Column(db.String(30), default="pending")  # pending, confirmed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    customization_notes = db.Column(db.Text)  # e.g. size, paper type, design notes
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship("Service")

    @property
    def subtotal(self):
        return round(self.service.price * self.quantity, 2)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, default=lambda: generate_reference("ORD"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), default="pending")  # pending, paid, processing, shipped, completed, cancelled
    shipping_address = db.Column(db.String(255))
    payment_method = db.Column(db.String(50), default="pay_on_pickup")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    service_name = db.Column(db.String(150))  # snapshot at time of order
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)

    service = db.relationship("Service")

    @property
    def subtotal(self):
        return round(self.unit_price * self.quantity, 2)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# app/models.py
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
    
    preferred_theme = db.Column(db.String(20), default="light")
    preferred_currency = db.Column(db.String(10), default="NGN")
    address = db.Column(db.String(255), nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - Using back_populates everywhere
    bookings = db.relationship(
        "Booking", 
        foreign_keys="Booking.user_id",
        back_populates="customer", 
        lazy=True
    )
    orders = db.relationship("Order", back_populates="customer", lazy=True)
    cart_items = db.relationship("CartItem", back_populates="owner", lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="author", lazy=True)
    
    assigned_bookings = db.relationship(
        "Booking",
        foreign_keys="Booking.assigned_staff_id",
        back_populates="assigned_staff",
        lazy=True
    )

    # Wishlist
    wishlist_items = db.relationship("Wishlist", back_populates="user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", lazy=True, cascade="all, delete-orphan")
    activities = db.relationship("ActivityLog", back_populates="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def cart_total(self):
        return sum(item.subtotal for item in self.cart_items)

    @property
    def cart_count(self):
        return sum(item.quantity for item in self.cart_items)

    @property
    def total_orders(self):
        return Order.query.filter_by(user_id=self.id).count()

    @property
    def total_spent(self):
        result = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.user_id == self.id,
            Order.status.in_(['paid', 'completed', 'shipped'])
        ).scalar()
        return result or 0.0

    @property
    def pending_orders(self):
        return Order.query.filter_by(user_id=self.id, status='pending').count()

    @property
    def completed_bookings(self):
        return Booking.query.filter_by(user_id=self.id, status='completed').count()

    def __repr__(self):
        return f"<User {self.email}>"


class ServiceCategory(db.Model):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default="printer")
    description = db.Column(db.String(255))
    
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = db.relationship("Service", back_populates="category", lazy=True)

    def __repr__(self):
        return f"<ServiceCategory {self.name}>"


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
    
    additional_images = db.Column(db.Text, nullable=True)

    price = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(50), default="item")
    
    compare_at_price = db.Column(db.Float, nullable=True)
    is_on_sale = db.Column(db.Boolean, default=False)
    sale_start_date = db.Column(db.DateTime, nullable=True)
    sale_end_date = db.Column(db.DateTime, nullable=True)

    estimated_delivery_days = db.Column(db.Integer, default=3)
    has_express_option = db.Column(db.Boolean, default=False)
    express_price_multiplier = db.Column(db.Float, default=1.5)

    is_bookable = db.Column(db.Boolean, default=False)
    is_purchasable = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    stock_quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)
    track_inventory = db.Column(db.Boolean, default=False)

    meta_title = db.Column(db.String(100), nullable=True)
    meta_description = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - Using back_populates consistently
    category = db.relationship("ServiceCategory", back_populates="services")
    bookings = db.relationship("Booking", back_populates="service", lazy=True)
    reviews = db.relationship("Review", back_populates="service", lazy=True)
    order_items = db.relationship("OrderItem", back_populates="service", lazy=True)
    wishlist_entries = db.relationship("Wishlist", back_populates="service", lazy=True, cascade="all, delete-orphan")

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    @property
    def rating_count(self):
        return len(self.reviews)

    @property
    def review_stars(self):
        return int(round(self.average_rating))

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0

    @property
    def stock_status(self):
        if not self.track_inventory:
            return "in_stock"
        if self.stock_quantity <= 0:
            return "out_of_stock"
        if self.stock_quantity <= self.low_stock_threshold:
            return "low_stock"
        return "in_stock"

    @property
    def display_price(self):
        if self.is_on_sale and self.compare_at_price and self.compare_at_price > self.price:
            return self.compare_at_price
        return self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale and self.compare_at_price and self.compare_at_price > self.price:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0

    @property
    def express_price(self):
        if self.has_express_option:
            return round(self.price * self.express_price_multiplier, 2)
        return None

    def get_delivery_message(self):
        if not self.is_purchasable:
            return "Not available for delivery"
        if self.estimated_delivery_days <= 0:
            return "Ready immediately"
        elif self.estimated_delivery_days == 1:
            return "Ready in 1 business day"
        elif self.estimated_delivery_days <= 3:
            return f"Ready in {self.estimated_delivery_days} business days"
        else:
            return f"Ready in {self.estimated_delivery_days} business days"

    def reduce_stock(self, quantity):
        if self.track_inventory:
            if self.stock_quantity < quantity:
                raise ValueError(f"Insufficient stock for {self.name}")
            self.stock_quantity -= quantity

    def __repr__(self):
        return f"<Service {self.name}>"


class Booking(db.Model):
    """A scheduled session: photo shoot, video coverage, event consultation, etc."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, default=lambda: generate_reference("BKG"))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)

    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(255))
    event_type = db.Column(db.String(100))
    notes = db.Column(db.Text)

    status = db.Column(db.String(30), default="pending")
    
    guest_count = db.Column(db.Integer, nullable=True)
    estimated_duration = db.Column(db.Integer, nullable=True)
    special_requests = db.Column(db.Text, nullable=True)
    
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id", name="fk_booking_assigned_staff"), nullable=True)
    
    payment_status = db.Column(db.String(20), default="unpaid")
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Relationships - Using back_populates consistently
    customer = db.relationship("User", foreign_keys=[user_id], back_populates="bookings")
    assigned_staff = db.relationship("User", foreign_keys=[assigned_staff_id], back_populates="assigned_bookings")
    service = db.relationship("Service", back_populates="bookings")

    @property
    def is_upcoming(self):
        from datetime import date
        if self.status in ['cancelled', 'completed']:
            return False
        return self.preferred_date >= date.today()

    @property
    def display_date(self):
        return self.preferred_date.strftime('%A, %B %d, %Y')

    @property
    def display_time(self):
        return self.preferred_time.strftime('%I:%M %p')

    def __repr__(self):
        return f"<Booking {self.reference}>"


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    customization_notes = db.Column(db.Text)
    options = db.Column(db.Text, nullable=True)
    
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    service = db.relationship("Service")
    owner = db.relationship("User", back_populates="cart_items")

    @property
    def subtotal(self):
        return round(self.service.price * self.quantity, 2)

    def __repr__(self):
        return f"<CartItem {self.service.name} x{self.quantity}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, default=lambda: generate_reference("ORD"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), default="pending")
    
    shipping_address = db.Column(db.String(255))
    billing_address = db.Column(db.String(255), nullable=True)
    order_notes = db.Column(db.Text, nullable=True)
    
    payment_method = db.Column(db.String(50), default="pay_on_pickup")
    
    payment_reference = db.Column(db.String(100), unique=True, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    payment_details = db.Column(db.Text, nullable=True)
    
    tracking_number = db.Column(db.String(100), nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    discount_amount = db.Column(db.Float, default=0.0)
    discount_code = db.Column(db.String(50), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship("OrderItem", back_populates="order", lazy=True, cascade="all, delete-orphan")
    customer = db.relationship("User", back_populates="orders")

    @property
    def total_after_discount(self):
        return round(self.total_amount - self.discount_amount, 2)

    @property
    def is_paid(self):
        return self.status in ['paid', 'processing', 'shipped', 'completed']

    @property
    def can_cancel(self):
        return self.status in ['pending', 'paid']

    @property
    def status_badge(self):
        status_colors = {
            'pending': 'yellow',
            'paid': 'blue',
            'processing': 'purple',
            'shipped': 'indigo',
            'completed': 'green',
            'cancelled': 'red'
        }
        return status_colors.get(self.status, 'gray')

    @property
    def status_display(self):
        display_map = {
            'pending': 'Pending Payment',
            'paid': 'Paid',
            'processing': 'Processing',
            'shipped': 'Shipped',
            'completed': 'Completed',
            'cancelled': 'Cancelled'
        }
        return display_map.get(self.status, self.status.title())

    def __repr__(self):
        return f"<Order {self.reference}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    service_name = db.Column(db.String(150))
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    options = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    service = db.relationship("Service", back_populates="order_items")
    order = db.relationship("Order", back_populates="items")

    @property
    def subtotal(self):
        return round(self.unit_price * self.quantity, 2)

    def __repr__(self):
        return f"<OrderItem {self.service_name} x{self.quantity}>"


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    
    is_verified = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship("User", back_populates="reviews")
    service = db.relationship("Service", back_populates="reviews")

    @property
    def rating_stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)

    def __repr__(self):
        return f"<Review {self.id} - {self.rating}★>"


class Wishlist(db.Model):
    __tablename__ = "wishlists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="wishlist_items")
    service = db.relationship("Service", back_populates="wishlist_entries")

    __table_args__ = (db.UniqueConstraint('user_id', 'service_id', name='unique_wishlist'),)

    def __repr__(self):
        return f"<Wishlist {self.user_id} - {self.service_id}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(50), default="info")
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<ActivityLog {self.action} - {self.created_at}>"
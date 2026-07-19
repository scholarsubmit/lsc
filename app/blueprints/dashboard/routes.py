from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models import Booking, Order

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def overview():
    recent_bookings = (
        Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).limit(5).all()
    )
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template("dashboard/overview.html", bookings=recent_bookings, orders=recent_orders)


@dashboard_bp.route("/bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template("dashboard/bookings.html", bookings=bookings)


@dashboard_bp.route("/orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("dashboard/orders.html", orders=orders)


@dashboard_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("dashboard/order_detail.html", order=order)

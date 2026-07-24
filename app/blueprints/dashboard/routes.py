# app/blueprints/dashboard/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Order, Booking

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/orders")
@login_required
def orders():
    """View all orders for the current user."""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("dashboard/orders.html", orders=orders)


@dashboard_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    """View a specific order detail."""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("dashboard/order_detail.html", order=order)


@dashboard_bp.route("/bookings")
@login_required
def bookings():
    """View all bookings for the current user."""
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template("dashboard/bookings.html", bookings=bookings)


@dashboard_bp.route("/bookings/<int:booking_id>")
@login_required
def booking_detail(booking_id):
    """View a specific booking detail."""
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    return render_template("dashboard/booking_detail.html", booking=booking)


@dashboard_bp.route("/cancel-booking/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking."""
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    
    if booking.status in ['cancelled', 'completed']:
        flash("This booking cannot be cancelled.", "error")
        return redirect(url_for('dashboard.bookings'))
    
    booking.status = 'cancelled'
    booking.cancelled_at = datetime.utcnow()
    db.session.commit()
    
    flash(f"Booking {booking.reference} has been cancelled.", "info")
    return redirect(url_for('dashboard.bookings'))


# Keep these as aliases if you want backward compatibility
@dashboard_bp.route("/my-orders")
@login_required
def my_orders():
    """Alias for orders - keeps backward compatibility."""
    return redirect(url_for('dashboard.orders'))


@dashboard_bp.route("/my-bookings")
@login_required
def my_bookings():
    """Alias for bookings - keeps backward compatibility."""
    return redirect(url_for('dashboard.bookings'))


@dashboard_bp.route("/profile")
@login_required
def profile():
    """View user profile."""
    return render_template("dashboard/profile.html", user=current_user)


@dashboard_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", current_user.full_name)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.address = request.form.get("address", current_user.address)
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard.profile'))
    
    return render_template("dashboard/edit_profile.html", user=current_user)
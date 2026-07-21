import os
import uuid
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Service, ServiceCategory, Order, Booking, User

admin_bp = Blueprint("admin", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def admin_required(view_func):
    """Restricts a view to logged-in users with is_admin=True (the CEO / staff account)."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access the admin area.", "info")
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def _allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _save_uploaded_image(file_storage):
    """Saves an uploaded image under static/img/services and returns its relative path,
    or None if no valid file was provided."""
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed_image(file_storage.filename):
        flash("Image must be a JPG, PNG, GIF, or WEBP file.", "error")
        return None

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = os.path.join(current_app.static_folder, "img", "services")
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, filename))
    return f"img/services/{filename}"


# ---------------------------------------------------------------- Dashboard

@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "total_services": Service.query.count(),
        "active_services": Service.query.filter_by(is_active=True).count(),
        "total_orders": Order.query.count(),
        "pending_orders": Order.query.filter_by(status="pending").count(),
        "total_bookings": Booking.query.count(),
        "pending_bookings": Booking.query.filter_by(status="pending").count(),
        "total_customers": User.query.filter_by(is_admin=False).count(),
        "revenue": db.session.query(db.func.coalesce(db.func.sum(Order.total_amount), 0.0))
        .filter(Order.status != "cancelled").scalar(),
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(6).all()
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders, recent_bookings=recent_bookings)


# ---------------------------------------------------------------- Services

@admin_bp.route("/services")
@admin_required
def services():
    all_services = Service.query.order_by(Service.created_at.desc()).all()
    return render_template("admin/services.html", services=all_services)


@admin_bp.route("/services/new", methods=["GET", "POST"])
@admin_required
def new_service():
    categories = ServiceCategory.query.all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id")
        price = request.form.get("price", "0")
        unit = request.form.get("unit", "item").strip()
        short_description = request.form.get("short_description", "").strip()
        description = request.form.get("description", "").strip()

        error = None
        if not name or not category_id:
            error = "Name and category are required."
        try:
            price = float(price)
        except ValueError:
            error = "Price must be a number."

        slug = _slugify(name)
        if Service.query.filter_by(slug=slug).first():
            error = "A service with a very similar name already exists."

        if error:
            flash(error, "error")
            return render_template("admin/service_form.html", categories=categories, service=None, form_data=request.form)

        image_path = _save_uploaded_image(request.files.get("image")) or "img/placeholder-service.jpg"

        service = Service(
            category_id=int(category_id),
            name=name,
            slug=slug,
            short_description=short_description,
            description=description,
            price=price,
            unit=unit or "item",
            image=image_path,
            is_bookable=bool(request.form.get("is_bookable")),
            is_purchasable=bool(request.form.get("is_purchasable")),
            is_featured=bool(request.form.get("is_featured")),
            is_active=bool(request.form.get("is_active", "on")),
        )
        db.session.add(service)
        db.session.commit()
        flash(f'"{service.name}" was added to the catalog.', "success")
        return redirect(url_for("admin.services"))

    return render_template("admin/service_form.html", categories=categories, service=None, form_data={})


@admin_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    categories = ServiceCategory.query.all()

    if request.method == "POST":
        service.name = request.form.get("name", service.name).strip()
        service.category_id = int(request.form.get("category_id", service.category_id))
        service.short_description = request.form.get("short_description", "").strip()
        service.description = request.form.get("description", "").strip()
        service.unit = request.form.get("unit", service.unit).strip()

        try:
            service.price = float(request.form.get("price", service.price))
        except ValueError:
            flash("Price must be a number.", "error")
            return render_template("admin/service_form.html", categories=categories, service=service, form_data=request.form)

        new_image = _save_uploaded_image(request.files.get("image"))
        if new_image:
            service.image = new_image

        service.is_bookable = bool(request.form.get("is_bookable"))
        service.is_purchasable = bool(request.form.get("is_purchasable"))
        service.is_featured = bool(request.form.get("is_featured"))
        service.is_active = bool(request.form.get("is_active"))

        db.session.commit()
        flash(f'"{service.name}" was updated.', "success")
        return redirect(url_for("admin.services"))

    return render_template("admin/service_form.html", categories=categories, service=service, form_data={})


@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@admin_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    name = service.name
    db.session.delete(service)
    db.session.commit()
    flash(f'"{name}" was removed from the catalog.', "info")
    return redirect(url_for("admin.services"))


@admin_bp.route("/services/<int:service_id>/toggle/<field>", methods=["POST"])
@admin_required
def toggle_service_field(service_id, field):
    service = Service.query.get_or_404(service_id)
    if field in {"is_active", "is_featured", "is_bookable", "is_purchasable"}:
        setattr(service, field, not getattr(service, field))
        db.session.commit()
    return redirect(request.referrer or url_for("admin.services"))


def _slugify(text):
    return (
        text.lower()
        .replace("&", "and")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
        .replace("  ", " ")
        .replace(" ", "-")
    )


# ---------------------------------------------------------------- Categories

@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        icon = request.form.get("icon", "printer").strip() or "printer"

        if not name:
            flash("Category name is required.", "error")
        elif ServiceCategory.query.filter_by(name=name).first():
            flash("A category with this name already exists.", "error")
        else:
            cat = ServiceCategory(name=name, slug=_slugify(name), description=description, icon=icon)
            db.session.add(cat)
            db.session.commit()
            flash(f'Category "{name}" created.', "success")
        return redirect(url_for("admin.categories"))

    all_categories = ServiceCategory.query.all()
    return render_template("admin/categories.html", categories=all_categories)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = ServiceCategory.query.get_or_404(category_id)
    if category.services:
        flash("Move or delete this category's services before deleting it.", "error")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------- Orders

@admin_bp.route("/orders")
@admin_required
def orders():
    status_filter = request.args.get("status")
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_orders = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=all_orders, status_filter=status_filter)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in {"pending", "paid", "processing", "shipped", "completed", "cancelled"}:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.reference} marked as {new_status}.", "success")
    return redirect(request.referrer or url_for("admin.orders"))


# ---------------------------------------------------------------- Bookings

@admin_bp.route("/bookings")
@admin_required
def bookings():
    status_filter = request.args.get("status")
    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings, status_filter=status_filter)


@admin_bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
@admin_required
def update_booking_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get("status")
    if new_status in {"pending", "confirmed", "completed", "cancelled"}:
        booking.status = new_status
        db.session.commit()
        flash(f"Booking {booking.reference} marked as {new_status}.", "success")
    return redirect(request.referrer or url_for("admin.bookings"))

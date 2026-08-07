import os
import uuid
import json
from functools import wraps
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, abort, jsonify, send_from_directory
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Service, ServiceCategory, Order, OrderItem, Booking, User,
    Notification, Ad, CurrencyRate, PushSubscription,
)

admin_bp = Blueprint("admin", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ORDER_STATUSES = Order.STATUS_FLOW + ["cancelled"]


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
    stats["pending_orders"] = Order.query.filter_by(status="awaiting_approval").count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(6).all()
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders, recent_bookings=recent_bookings)


@admin_bp.context_processor
def inject_unread_notifications():
    if current_user.is_authenticated and getattr(current_user, "is_admin", False):
        try:
            count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        except Exception:
            count = 0
        return {"admin_unread_notifications": count}
    return {"admin_unread_notifications": 0}


# ---------------------------------------------------------------- Services

@admin_bp.route("/services")
@admin_required
def services():
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Service.query
    if search:
        like = f"%{search}%"
        query = query.filter(Service.name.ilike(like))
    pagination = query.order_by(Service.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/services.html", services=pagination.items, pagination=pagination, search=search)


#Updated the new_service and edit_service functions

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
        
        # NEW: Get delivery fields
        estimated_delivery_days = request.form.get("estimated_delivery_days", 3)
        has_express_option = bool(request.form.get("has_express_option"))
        express_price_multiplier = request.form.get("express_price_multiplier", 1.5)

        # ── Print configurator fields ──
        is_dimensional = bool(request.form.get("is_dimensional"))
        price_per_sqft = request.form.get("price_per_sqft", "0").strip() or "0"
        requires_upload = bool(request.form.get("requires_upload"))
        max_upload_mb = request.form.get("max_upload_mb", "50").strip() or "50"
        preset_sizes_json = _parse_preset_sizes(request.form.get("preset_sizes_raw", ""))

        error = None
        if not name or not category_id:
            error = "Name and category are required."
        try:
            price = float(price)
            estimated_delivery_days = int(estimated_delivery_days)
            price_per_sqft = float(price_per_sqft)
            max_upload_mb = int(max_upload_mb)
        except ValueError:
            error = "Price must be a number and delivery days must be a whole number."

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
            # NEW delivery fields
            estimated_delivery_days=estimated_delivery_days,
            has_express_option=has_express_option,
            express_price_multiplier=float(express_price_multiplier),
            is_bookable=bool(request.form.get("is_bookable")),
            is_purchasable=bool(request.form.get("is_purchasable")),
            is_featured=bool(request.form.get("is_featured")),
            is_active=bool(request.form.get("is_active", "on")),
            is_dimensional=is_dimensional,
            price_per_sqft=price_per_sqft,
            preset_sizes=preset_sizes_json,
            requires_upload=requires_upload,
            max_upload_mb=max_upload_mb,
        )
        db.session.add(service)
        db.session.commit()
        flash(f'"{service.name}" was added to the catalog.', "success")
        return redirect(url_for("admin.services"))

    return render_template("admin/service_form.html", categories=categories, service=None, form_data={})


def _parse_preset_sizes(raw_text):
    """Parses simple lines like '2x3=2x3 ft' or just '2x3' into the JSON list
    the print configurator expects: [{"label","width_ft","height_ft"}, ...].
    One size per line, format: WIDTHxHEIGHT or WIDTHxHEIGHT|Custom Label."""
    if not raw_text or not raw_text.strip():
        return None
    sizes = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        label_override = None
        if "|" in line:
            line, label_override = line.split("|", 1)
            line = line.strip()
            label_override = label_override.strip()
        if "x" not in line.lower():
            continue
        parts = line.lower().replace(" ", "").split("x")
        if len(parts) != 2:
            continue
        try:
            w, h = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        label = label_override or f"{w:g} x {h:g} ft"
        sizes.append({"label": label, "width_ft": w, "height_ft": h})
    return json.dumps(sizes) if sizes else None


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

        # NEW: Update delivery fields
        try:
            service.estimated_delivery_days = int(request.form.get("estimated_delivery_days", service.estimated_delivery_days))
            service.express_price_multiplier = float(request.form.get("express_price_multiplier", service.express_price_multiplier))
        except ValueError:
            flash("Delivery days must be a whole number and multiplier must be a number.", "error")
            return render_template("admin/service_form.html", categories=categories, service=service, form_data=request.form)

        service.has_express_option = bool(request.form.get("has_express_option"))

        try:
            service.price = float(request.form.get("price", service.price))
        except ValueError:
            flash("Price must be a number.", "error")
            return render_template("admin/service_form.html", categories=categories, service=service, form_data=request.form)

        # ── Print configurator fields ──
        service.is_dimensional = bool(request.form.get("is_dimensional"))
        service.requires_upload = bool(request.form.get("requires_upload"))
        try:
            service.price_per_sqft = float(request.form.get("price_per_sqft", service.price_per_sqft) or 0)
            service.max_upload_mb = int(request.form.get("max_upload_mb", service.max_upload_mb) or 50)
        except ValueError:
            flash("Price per sq ft and max upload size must be numbers.", "error")
            return render_template("admin/service_form.html", categories=categories, service=service, form_data=request.form)
        new_presets = _parse_preset_sizes(request.form.get("preset_sizes_raw", ""))
        if new_presets is not None:
            service.preset_sizes = new_presets
        elif not request.form.get("preset_sizes_raw", "").strip():
            service.preset_sizes = None

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
    highlight = request.args.get("highlight", type=int)
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        like = f"%{search}%"
        query = query.join(User, Order.user_id == User.id).filter(
            db.or_(Order.reference.ilike(like), User.full_name.ilike(like), User.email.ilike(like))
        )
    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template(
        "admin/orders.html", orders=pagination.items, pagination=pagination, status_filter=status_filter,
        order_statuses=ORDER_STATUSES, highlight=highlight, search=search,
    )


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in ORDER_STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.reference} marked as {order.status_display}.", "success")
    return redirect(request.referrer or url_for("admin.orders"))


@admin_bp.route("/orders/<int:order_id>/approve", methods=["POST"])
@admin_required
def approve_order(order_id):
    """One-click approve-and-book from the orders list or notification link."""
    order = Order.query.get_or_404(order_id)
    if order.status == "awaiting_approval":
        order.status = "approved"
        db.session.commit()
        db.session.add(Notification(
            user_id=order.user_id,
            type="order_update",
            title="Order approved",
            message=f"Your order {order.reference} was approved and booked for production.",
            link=f"/dashboard/orders/{order.id}",
        ))
        db.session.commit()
        flash(f"Order {order.reference} approved and booked for production.", "success")
    return redirect(request.referrer or url_for("admin.orders"))


@admin_bp.route("/orders/<int:order_id>/download/<int:item_id>")
@admin_required
def download_design_file(order_id, item_id):
    """Securely serve a customer's uploaded print-job design file — admin-only."""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.filter_by(id=item_id, order_id=order.id).first_or_404()
    opts = item.options_dict
    rel_path = opts.get("upload_path")
    if not rel_path:
        abort(404)
    directory = current_app.config["UPLOAD_FOLDER"]
    download_name = opts.get("upload_original_name") or os.path.basename(rel_path)
    return send_from_directory(directory, rel_path, as_attachment=True, download_name=download_name)


# ---------------------------------------------------------------- Bookings

@admin_bp.route("/bookings")
@admin_required
def bookings():
    status_filter = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Booking.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/bookings.html", bookings=pagination.items, pagination=pagination, status_filter=status_filter)


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


# ---------------------------------------------------------------- Notifications

@admin_bp.route("/notifications")
@admin_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return render_template("admin/notifications.html", notifications=items)


@admin_bp.route("/notifications/unread-count")
@admin_required
def notifications_unread_count():
    """Polled every ~15s by the admin sidebar bell for a near-real-time badge."""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": count})


@admin_bp.route("/notifications/feed")
@admin_required
def notifications_feed():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    return jsonify({
        "unread_count": Notification.query.filter_by(user_id=current_user.id, is_read=False).count(),
        "items": [
            {
                "id": n.id, "title": n.title, "message": n.message,
                "link": n.link, "is_read": n.is_read,
                "created_at": n.created_at.strftime("%b %d, %I:%M %p"),
            }
            for n in items
        ],
    })


@admin_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@admin_required
def mark_notification_read(notification_id):
    n = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})
    return redirect(n.link or url_for("admin.notifications"))


@admin_bp.route("/notifications/mark-all-read", methods=["POST"])
@admin_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True}) if request.headers.get("X-Requested-With") == "XMLHttpRequest" else redirect(url_for("admin.notifications"))


# ---------------------------------------------------------------- Web Push subscriptions

@admin_bp.route("/push/vapid-public-key")
@admin_required
def push_public_key():
    return jsonify({"publicKey": current_app.config.get("VAPID_PUBLIC_KEY", "")})


@admin_bp.route("/push/subscribe", methods=["POST"])
@admin_required
def push_subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys", {})
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return jsonify({"success": False, "message": "Invalid subscription."}), 400

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not existing:
        db.session.add(PushSubscription(
            user_id=current_user.id, endpoint=endpoint,
            p256dh=keys["p256dh"], auth=keys["auth"],
        ))
        db.session.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------- Currency management

@admin_bp.route("/currencies", methods=["GET", "POST"])
@admin_required
def currencies():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        symbol = request.form.get("symbol", "").strip()
        rate = request.form.get("rate_per_ngn", "").strip()

        error = None
        if not code or not name or not symbol:
            error = "Code, name, and symbol are required."
        else:
            try:
                rate = float(rate)
            except ValueError:
                error = "Rate must be a number."

        if error:
            flash(error, "error")
        elif CurrencyRate.query.filter_by(code=code).first():
            flash(f"{code} already exists — edit it below instead.", "error")
        else:
            db.session.add(CurrencyRate(code=code, name=name, symbol=symbol, rate_per_ngn=rate))
            db.session.commit()
            flash(f"{code} added.", "success")
        return redirect(url_for("admin.currencies"))

    all_currencies = CurrencyRate.query.order_by(CurrencyRate.code.asc()).all()
    return render_template("admin/currencies.html", currencies=all_currencies)


@admin_bp.route("/currencies/<int:currency_id>/update", methods=["POST"])
@admin_required
def update_currency(currency_id):
    c = CurrencyRate.query.get_or_404(currency_id)
    try:
        c.rate_per_ngn = float(request.form.get("rate_per_ngn", c.rate_per_ngn))
        c.symbol = request.form.get("symbol", c.symbol).strip() or c.symbol
        c.name = request.form.get("name", c.name).strip() or c.name
        db.session.commit()
        flash(f"{c.code} rate updated.", "success")
    except ValueError:
        flash("Rate must be a number.", "error")
    return redirect(url_for("admin.currencies"))


@admin_bp.route("/currencies/<int:currency_id>/toggle", methods=["POST"])
@admin_required
def toggle_currency(currency_id):
    c = CurrencyRate.query.get_or_404(currency_id)
    if c.code == "NGN":
        flash("The base currency (NGN) can't be disabled.", "error")
    else:
        c.is_active = not c.is_active
        db.session.commit()
    return redirect(url_for("admin.currencies"))


@admin_bp.route("/currencies/<int:currency_id>/delete", methods=["POST"])
@admin_required
def delete_currency(currency_id):
    c = CurrencyRate.query.get_or_404(currency_id)
    if c.code == "NGN":
        flash("The base currency (NGN) can't be deleted.", "error")
    else:
        db.session.delete(c)
        db.session.commit()
        flash(f"{c.code} removed.", "info")
    return redirect(url_for("admin.currencies"))


# ---------------------------------------------------------------- Landing page ads

@admin_bp.route("/ads", methods=["GET", "POST"])
@admin_required
def ads():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        badge_text = request.form.get("badge_text", "Promo").strip() or "Promo"
        link_url = request.form.get("link_url", "").strip() or None

        if not title or not message:
            flash("Title and message are required.", "error")
        else:
            ad = Ad(title=title, message=message, badge_text=badge_text, link_url=link_url)
            db.session.add(ad)
            db.session.commit()
            flash("Ad created and now live on the homepage.", "success")
        return redirect(url_for("admin.ads"))

    all_ads = Ad.query.order_by(Ad.display_order.asc(), Ad.created_at.desc()).all()
    return render_template("admin/ads.html", ads=all_ads)


@admin_bp.route("/ads/<int:ad_id>/toggle", methods=["POST"])
@admin_required
def toggle_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.is_active = not ad.is_active
    db.session.commit()
    return redirect(url_for("admin.ads"))


@admin_bp.route("/ads/<int:ad_id>/delete", methods=["POST"])
@admin_required
def delete_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    flash("Ad removed.", "info")
    return redirect(url_for("admin.ads"))

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Service, CartItem, Order, OrderItem

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/")
@login_required
def view_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.subtotal for item in items)
    return render_template("cart/view.html", items=items, total=total)


@cart_bp.route("/add/<slug>", methods=["POST"])
@login_required
def add_to_cart(slug):
    service = Service.query.filter_by(slug=slug, is_purchasable=True, is_active=True).first_or_404()
    quantity = max(1, int(request.form.get("quantity", 1)))
    notes = request.form.get("customization_notes", "").strip()

    existing = CartItem.query.filter_by(user_id=current_user.id, service_id=service.id).first()
    if existing:
        existing.quantity += quantity
        if notes:
            existing.customization_notes = notes
    else:
        db.session.add(
            CartItem(user_id=current_user.id, service_id=service.id, quantity=quantity, customization_notes=notes)
        )
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        count = sum(i.quantity for i in CartItem.query.filter_by(user_id=current_user.id).all())
        return jsonify({"success": True, "message": f"{service.name} added to cart.", "cart_count": count})

    flash(f"{service.name} added to your cart.", "success")
    return redirect(request.referrer or url_for("catalog.list_services"))


@cart_bp.route("/update/<int:item_id>", methods=["POST"])
@login_required
def update_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    quantity = int(request.form.get("quantity", 1))

    if quantity <= 0:
        db.session.delete(item)
        flash("Item removed from cart.", "info")
    else:
        item.quantity = quantity
        flash("Cart updated.", "success")

    db.session.commit()
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("catalog.list_services"))

    total = sum(item.subtotal for item in items)

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address", "").strip()
        payment_method = request.form.get("payment_method", "pay_on_pickup")

        order = Order(
            user_id=current_user.id,
            total_amount=total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            status="pending",
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for item in items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    service_id=item.service_id,
                    service_name=item.service.name,
                    unit_price=item.service.price,
                    quantity=item.quantity,
                )
            )
            db.session.delete(item)

        db.session.commit()
        flash(f"Order placed! Your reference is {order.reference}.", "success")
        return redirect(url_for("dashboard.order_detail", order_id=order.id))

    return render_template("cart/checkout.html", items=items, total=total)

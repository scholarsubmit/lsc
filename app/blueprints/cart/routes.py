# app/blueprints/cart/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging

from app.extensions import db
from app.models import Service, CartItem, Order, OrderItem

cart_bp = Blueprint("cart", __name__)
logger = logging.getLogger(__name__)


@cart_bp.route("/")
@login_required
def view_cart():
    """View current user's cart."""
    try:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.subtotal for item in items)
        item_count = sum(item.quantity for item in items)
        
        return render_template(
            "cart/view.html", 
            items=items, 
            total=total,
            item_count=item_count
        )
    except Exception as e:
        logger.error(f"Error viewing cart: {e}")
        flash("Unable to load your cart. Please try again.", "error")
        return redirect(url_for('catalog.list_services'))


@cart_bp.route("/add/<slug>", methods=["GET", "POST"])
@login_required
def add_to_cart(slug):
    """Add item to cart with AJAX support."""
    # Handle GET requests - redirect to service detail
    if request.method == "GET":
        flash("Please use the 'Add to Cart' button to add items.", "info")
        return redirect(url_for('catalog.detail', slug=slug))
    
    try:
        service = Service.query.filter_by(
            slug=slug, 
            is_purchasable=True, 
            is_active=True
        ).first_or_404()
        
        quantity = max(1, int(request.form.get("quantity", 1)))
        notes = request.form.get("customization_notes", "").strip()

        # Check if item already in cart
        existing = CartItem.query.filter_by(
            user_id=current_user.id, 
            service_id=service.id
        ).first()
        
        if existing:
            existing.quantity += quantity
            if notes:
                existing.customization_notes = notes
        else:
            db.session.add(
                CartItem(
                    user_id=current_user.id, 
                    service_id=service.id, 
                    quantity=quantity, 
                    customization_notes=notes
                )
            )
        
        db.session.commit()
        
        # Get updated cart count
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in cart_items)
        total = sum(item.subtotal for item in cart_items)

        # AJAX response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": True,
                "message": f"{service.name} added to cart.",
                "cart_count": count,
                "cart_total": total,
                "item_name": service.name
            })

        flash(f"{service.name} added to your cart.", "success")
        
        # Check if there's a next parameter
        next_url = request.form.get("next") or request.referrer
        if next_url and next_url != request.url:
            return redirect(next_url)
        return redirect(url_for("cart.view_cart"))
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": False,
                "message": "Error adding item to cart. Please try again."
            }), 500
        flash("Error adding item to cart. Please try again.", "error")
        return redirect(request.referrer or url_for("catalog.list_services"))


@cart_bp.route("/update/<int:item_id>", methods=["GET", "POST"])
@login_required
def update_item(item_id):
    """Update cart item quantity."""
    # Handle GET requests - redirect to cart
    if request.method == "GET":
        return redirect(url_for("cart.view_cart"))
    
    try:
        item = CartItem.query.filter_by(
            id=item_id, 
            user_id=current_user.id
        ).first_or_404()
        
        quantity = int(request.form.get("quantity", 1))

        if quantity <= 0:
            db.session.delete(item)
            message = f"{item.service.name} removed from cart."
            flash(message, "info")
        else:
            item.quantity = quantity
            message = "Cart updated."
            flash(message, "success")

        db.session.commit()
        
        # AJAX response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
            count = sum(item.quantity for item in cart_items)
            total = sum(item.subtotal for item in cart_items)
            return jsonify({
                "success": True,
                "message": message,
                "cart_count": count,
                "cart_total": total,
                "item_subtotal": item.subtotal if quantity > 0 else 0
            })

        return redirect(url_for("cart.view_cart"))
        
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": False,
                "message": "Error updating cart."
            }), 500
        flash("Error updating cart. Please try again.", "error")
        return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove/<int:item_id>", methods=["GET", "POST"])
@login_required
def remove_item(item_id):
    """Remove item from cart."""
    # Handle GET requests - redirect to cart
    if request.method == "GET":
        return redirect(url_for("cart.view_cart"))
    
    try:
        item = CartItem.query.filter_by(
            id=item_id, 
            user_id=current_user.id
        ).first_or_404()
        
        service_name = item.service.name
        db.session.delete(item)
        db.session.commit()
        
        # AJAX response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
            count = sum(item.quantity for item in cart_items)
            total = sum(item.subtotal for item in cart_items)
            return jsonify({
                "success": True,
                "message": f"{service_name} removed from cart.",
                "cart_count": count,
                "cart_total": total
            })

        flash(f"{service_name} removed from cart.", "info")
        return redirect(url_for("cart.view_cart"))
        
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": False,
                "message": "Error removing item."
            }), 500
        flash("Error removing item. Please try again.", "error")
        return redirect(url_for("cart.view_cart"))


@cart_bp.route("/count")
@login_required
def cart_count():
    """Return current user's cart count as JSON."""
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in cart_items)
        total = sum(item.subtotal for item in cart_items)
        return jsonify({
            "count": count,
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "name": item.service.name,
                    "quantity": item.quantity,
                    "subtotal": item.subtotal
                }
                for item in cart_items
            ]
        })
    except Exception as e:
        logger.error(f"Error getting cart count: {e}")
        return jsonify({"count": 0, "total": 0, "items": []}), 200


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Checkout page with order creation."""
    try:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not items:
            flash("Your cart is empty.", "info")
            return redirect(url_for("catalog.list_services"))

        total = sum(item.subtotal for item in items)

        if request.method == "POST":
            shipping_address = request.form.get("shipping_address", "").strip()
            payment_method = request.form.get("payment_method", "pay_on_pickup")
            order_notes = request.form.get("order_notes", "").strip()

            # Validate address if delivery is required
            if payment_method != "pay_on_pickup" and not shipping_address:
                flash("Please provide a delivery address.", "error")
                return render_template("cart/checkout.html", items=items, total=total)

            # Create order
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                shipping_address=shipping_address,
                payment_method=payment_method,
                status="pending",
                order_notes=order_notes
            )
            db.session.add(order)
            db.session.flush()

            # Create order items
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
            
            # Clear cart from session
            session.pop('cart_count', None)
            
            flash(f"Order placed! Your reference is {order.reference}.", "success")
            
            # Redirect to payment if using Paystack
            if payment_method == "paystack":
                return redirect(url_for("cart.initiate_payment", order_id=order.id))
            
            return redirect(url_for("dashboard.order_detail", order_id=order.id))

        return render_template("cart/checkout.html", items=items, total=total)
        
    except Exception as e:
        logger.error(f"Error during checkout: {e}")
        flash("Error during checkout. Please try again.", "error")
        return redirect(url_for("cart.view_cart"))


@cart_bp.route("/initiate-payment/<int:order_id>")
@login_required
def initiate_payment(order_id):
    """Initiate Paystack payment for an order."""
    try:
        order = Order.query.filter_by(
            id=order_id, 
            user_id=current_user.id
        ).first_or_404()
        
        if order.status == "paid":
            flash("This order has already been paid.", "info")
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
        
        # Check if Paystack is configured
        paystack_secret = current_app.config.get("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            flash("Payment gateway not configured. Please pay on pickup.", "warning")
            order.payment_method = "pay_on_pickup"
            db.session.commit()
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
        
        # Initialize Paystack payment
        import requests
        amount = int(order.total_amount * 100)  # Convert to kobo
        
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {paystack_secret}",
                "Content-Type": "application/json"
            },
            json={
                "email": current_user.email,
                "amount": amount,
                "reference": order.reference,
                "callback_url": url_for("cart.payment_callback", _external=True),
                "metadata": {
                    "order_id": order.id,
                    "user_id": current_user.id,
                    "custom_fields": [
                        {
                            "display_name": "Order Reference",
                            "variable_name": "order_ref",
                            "value": order.reference
                        }
                    ]
                }
            },
            timeout=10
        )
        
        data = response.json()
        if data.get("status"):
            order.payment_reference = data["data"]["reference"]
            db.session.commit()
            return redirect(data["data"]["authorization_url"])
        else:
            flash(f"Payment initialization failed: {data.get('message', 'Unknown error')}", "error")
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
            
    except Exception as e:
        logger.error(f"Payment initiation error: {e}")
        flash("Payment gateway error. Please try again or pay on pickup.", "error")
        return redirect(url_for("dashboard.order_detail", order_id=order.id))


@cart_bp.route("/payment-callback")
def payment_callback():
    """Handle Paystack callback after payment."""
    reference = request.args.get("reference")
    if not reference:
        flash("Invalid payment reference.", "error")
        return redirect(url_for("cart.view_cart"))
    
    try:
        # Find order by reference
        order = Order.query.filter_by(reference=reference).first()
        if not order:
            flash("Order not found.", "error")
            return redirect(url_for("cart.view_cart"))
        
        # Verify payment
        paystack_secret = current_app.config.get("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            flash("Payment gateway not configured.", "error")
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
        
        import requests
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {paystack_secret}"},
            timeout=10
        )
        
        data = response.json()
        if data.get("status") and data["data"]["status"] == "success":
            order.status = "paid"
            order.paid_at = datetime.utcnow()
            db.session.commit()
            
            # Send confirmation email (if configured)
            try:
                from app.utils.email import send_order_confirmation
                send_order_confirmation(order, order.customer)
            except:
                pass
            
            flash("Payment successful! Your order has been confirmed.", "success")
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
        else:
            flash("Payment verification failed. Please contact support.", "error")
            return redirect(url_for("dashboard.order_detail", order_id=order.id))
            
    except Exception as e:
        logger.error(f"Payment callback error: {e}")
        flash("Error verifying payment. Please contact support.", "error")
        return redirect(url_for("dashboard.order_detail", order_id=order.id))


@cart_bp.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    """Handle Paystack webhook for asynchronous events."""
    try:
        # Verify signature
        signature = request.headers.get("x-paystack-signature")
        paystack_secret = current_app.config.get("PAYSTACK_SECRET_KEY")
        
        if paystack_secret and signature:
            import hmac
            import hashlib
            computed = hmac.new(
                paystack_secret.encode(), 
                request.data, 
                hashlib.sha512
            ).hexdigest()
            if computed != signature:
                return "Invalid signature", 400
        
        event = request.json
        if event.get("event") == "charge.success":
            data = event.get("data", {})
            reference = data.get("reference")
            
            # Update order status
            order = Order.query.filter_by(reference=reference).first()
            if order and order.status != "paid":
                order.status = "paid"
                order.paid_at = datetime.utcnow()
                db.session.commit()
                
                # Send confirmation email
                try:
                    from app.utils.email import send_order_confirmation
                    send_order_confirmation(order, order.customer)
                except:
                    pass
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500


# Context processor for cart count
@cart_bp.context_processor
def inject_cart_count():
    """Inject cart count into all templates."""
    if current_user.is_authenticated:
        try:
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
            count = sum(item.quantity for item in cart_items)
            return {"cart_count": count}
        except:
            return {"cart_count": 0}
    return {"cart_count": 0}
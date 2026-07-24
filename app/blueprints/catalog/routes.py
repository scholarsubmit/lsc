# app/blueprints/catalog/routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Service, ServiceCategory, Review

catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.route("/")
def list_services():
    """List all active services with optional category filtering and search."""
    query = Service.query.filter_by(is_active=True)

    category_slug = request.args.get("category")
    search = request.args.get("q", "").strip()

    if category_slug:
        category = ServiceCategory.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)

    if search:
        query = query.filter(
            db.or_(
                Service.name.ilike(f"%{search}%"),
                Service.short_description.ilike(f"%{search}%"),
                Service.description.ilike(f"%{search}%")
            )
        )

    services = query.order_by(Service.is_featured.desc(), Service.name.asc()).all()
    categories = ServiceCategory.query.all()

    return render_template(
        "catalog/list.html",
        services=services,
        categories=categories,
        active_category=category_slug,
        search=search,
    )


@catalog_bp.route("/<slug>")
def detail(slug):
    """Service detail page with reviews and recommendations."""
    service = Service.query.filter_by(slug=slug, is_active=True).first_or_404()
    
    # Get reviews - FIXED: Query Review model directly
    reviews = Review.query.filter_by(service_id=service.id).order_by(Review.created_at.desc()).all()
    
    # --- RECOMMENDATIONS: "You Might Also Like" ---
    # 1. Same category, different service (prioritize featured)
    same_category = Service.query.filter(
        Service.category_id == service.category_id,
        Service.id != service.id,
        Service.is_active == True  # noqa: E712
    ).order_by(Service.is_featured.desc()).limit(4).all()
    
    # 2. If not enough, fill with other featured services
    if len(same_category) < 4:
        needed = 4 - len(same_category)
        other_services = Service.query.filter(
            Service.category_id != service.category_id,
            Service.id != service.id,
            Service.is_active == True,  # noqa: E712
            Service.is_featured == True  # noqa: E712
        ).limit(needed).all()
        same_category.extend(other_services)
    
    # 3. Similar priced services (±30%)
    if service.price > 0:
        price_range = service.price * 0.3
        similar_price = Service.query.filter(
            Service.id != service.id,
            Service.is_active == True,  # noqa: E712
            Service.price.between(max(0, service.price - price_range), service.price + price_range)
        ).limit(3).all()
    else:
        similar_price = []
    
    return render_template(
        'catalog/detail.html',
        service=service,
        reviews=reviews,
        recommendations=same_category[:4],
        similar_price=similar_price[:3]
    )


@catalog_bp.route("/<slug>/review", methods=["POST"])
@login_required
def add_review(slug):
    """Add a review for a service."""
    service = Service.query.filter_by(slug=slug, is_active=True).first_or_404()
    
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()

    # Validate rating
    if not rating or rating < 1 or rating > 5:
        flash("Please provide a valid rating between 1 and 5.", "error")
        return redirect(url_for("catalog.detail", slug=service.slug))

    # Check if user already reviewed this service
    existing = Review.query.filter_by(service_id=service.id, user_id=current_user.id).first()
    if existing:
        flash("You have already reviewed this service.", "info")
        return redirect(url_for("catalog.detail", slug=service.slug))

    # Create new review
    review = Review(
        service_id=service.id,
        user_id=current_user.id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    flash("Thanks for your review!", "success")
    return redirect(url_for("catalog.detail", slug=service.slug))


# Optional: Add a route to get service reviews as JSON (for AJAX)
@catalog_bp.route("/<slug>/reviews.json")
def get_reviews_json(slug):
    """Return service reviews as JSON (useful for AJAX loading)."""
    service = Service.query.filter_by(slug=slug, is_active=True).first_or_404()
    reviews = Review.query.filter_by(service_id=service.id).order_by(Review.created_at.desc()).all()
    
    return {
        "service": service.name,
        "average_rating": service.average_rating,
        "reviews": [
            {
                "rating": r.rating,
                "comment": r.comment,
                "author": r.author.full_name,
                "date": r.created_at.strftime("%B %d, %Y")
            }
            for r in reviews
        ]
    }


# Optional: Add a route for featured services (for homepage)
@catalog_bp.route("/featured")
def featured_services():
    """Get featured services."""
    services = Service.query.filter_by(is_active=True, is_featured=True).order_by(Service.created_at.desc()).all()
    return render_template("catalog/featured.html", services=services)
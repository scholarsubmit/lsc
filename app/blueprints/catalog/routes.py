from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Service, ServiceCategory, Review

catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.route("/")
def list_services():
    query = Service.query.filter_by(is_active=True)

    category_slug = request.args.get("category")
    search = request.args.get("q", "").strip()

    if category_slug:
        category = ServiceCategory.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)

    if search:
        query = query.filter(Service.name.ilike(f"%{search}%"))

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
    service = Service.query.filter_by(slug=slug, is_active=True).first_or_404()
    related = (
        Service.query.filter(
            Service.category_id == service.category_id,
            Service.id != service.id,
            Service.is_active == True,  # noqa: E712
        )
        .limit(4)
        .all()
    )
    return render_template("catalog/detail.html", service=service, related=related)


@catalog_bp.route("/<slug>/review", methods=["POST"])
@login_required
def add_review(slug):
    service = Service.query.filter_by(slug=slug).first_or_404()
    rating = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()

    review = Review(service_id=service.id, user_id=current_user.id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()

    flash("Thanks for your review!", "success")
    return redirect(url_for("catalog.detail", slug=slug))

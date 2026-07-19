from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app

from app.models import ServiceCategory, Service

main_bp = Blueprint("main", __name__)


@main_bp.route("/service-worker.js")
def service_worker():
    """Served at the root so its scope covers the entire site (required for PWA installability)."""
    response = send_from_directory(current_app.static_folder, "service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@main_bp.route("/")
def home():
    categories = ServiceCategory.query.all()
    featured = Service.query.filter_by(is_featured=True, is_active=True).limit(6).all()
    return render_template("index.html", categories=categories, featured=featured)


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/marketplace-insights")
def marketplace_insights():
    """A page reflecting on marketplace UX patterns (trust badges, ratings,
    flash deals) borrowed from large platforms like Jumia, Alibaba and Temu,
    adapted to a branded, single-company storefront."""
    return render_template("marketplace_insights.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Hook up an email service (e.g. Flask-Mail, SendGrid) here in production.
        flash("Thanks for reaching out! Our team will respond within 24 hours.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html")


@main_bp.route("/offline")
def offline():
    """Fallback page served by the service worker when there's no connection."""
    return render_template("offline.html")

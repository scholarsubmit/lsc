# app/blueprints/main/routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app, session
from flask_login import current_user, login_required
from app.models import ServiceCategory, Service, Booking, Order
from app.extensions import db
from datetime import datetime
import logging

main_bp = Blueprint("main", __name__)

# Setup logger
logger = logging.getLogger(__name__)


@main_bp.route("/service-worker.js")
def service_worker():
    """Served at the root so its scope covers the entire site (required for PWA installability)."""
    try:
        response = send_from_directory(current_app.static_folder, "service-worker.js")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"Error serving service worker: {e}")
        return "Service worker not found", 404


# CHANGE: Renamed from 'home' to 'index' to match template
@main_bp.route("/")
def index():
    """
    Homepage. Redirects logged-in users to their appropriate dashboard:
    - Admin → Admin Dashboard
    - Regular users → Services page
    - Guests → Landing page
    """
    # If user is logged in, redirect to appropriate page
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('catalog.list_services'))
    
    # For non-logged in users, show the landing page
    try:
        categories = ServiceCategory.query.all()
        featured = Service.query.filter_by(
            is_featured=True, 
            is_active=True
        ).order_by(Service.created_at.desc()).limit(6).all()
        
        # Get recent services for the "New Arrivals" section
        recent_services = Service.query.filter_by(
            is_active=True
        ).order_by(Service.created_at.desc()).limit(4).all()

        from app.models import Ad
        active_ads = [a for a in Ad.query.order_by(Ad.display_order.asc()).all() if a.is_currently_live]
        
        return render_template(
            "index.html",
            categories=categories,
            featured=featured,
            recent_services=recent_services,
            active_ads=active_ads,
            year=datetime.now().year
        )
    except Exception as e:
        logger.error(f"Error loading homepage: {e}")
        flash("Unable to load homepage. Please try again.", "error")
        return render_template("index.html", categories=[], featured=[], recent_services=[], active_ads=[])


@main_bp.route("/about")
def about():
    """About page with company information."""
    try:
        total_services = Service.query.filter_by(is_active=True).count()
        total_categories = ServiceCategory.query.count()
        
        return render_template(
            "about.html",
            total_services=total_services,
            total_categories=total_categories,
            year=datetime.now().year
        )
    except Exception as e:
        logger.error(f"Error loading about page: {e}")
        return render_template("about.html", total_services=0, total_categories=0)


@main_bp.route("/marketplace-insights")
def marketplace_insights():
    """A page reflecting on marketplace UX patterns (trust badges, ratings,
    flash deals) borrowed from large platforms like Jumia, Alibaba and Temu,
    adapted to a branded, single-company storefront."""
    try:
        return render_template("marketplace_insights.html", year=datetime.now().year)
    except Exception as e:
        logger.error(f"Error loading marketplace insights: {e}")
        flash("Unable to load marketplace insights.", "error")
        return redirect(url_for('main.index'))


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page with form submission."""
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            subject = request.form.get("subject", "").strip()
            message = request.form.get("message", "").strip()
            
            if not name or not email or not message:
                flash("Please fill in all required fields.", "error")
                return render_template("contact.html", form_data=request.form)
            
            if not "@" in email or not "." in email:
                flash("Please enter a valid email address.", "error")
                return render_template("contact.html", form_data=request.form)
            
            logger.info(f"Contact form submission from {name} ({email}): {subject}")
            
            flash("Thanks for reaching out! Our team will respond within 24 hours.", "success")
            return redirect(url_for("main.contact"))
            
        except Exception as e:
            logger.error(f"Error processing contact form: {e}")
            flash("An error occurred. Please try again.", "error")
            return render_template("contact.html", form_data=request.form)
    
    return render_template("contact.html", year=datetime.now().year)


@main_bp.route("/offline")
def offline():
    """Fallback page served by the service worker when there's no connection."""
    return render_template("offline.html", year=datetime.now().year)


@main_bp.route("/dashboard")
@login_required
def dashboard_redirect():
    """Redirect users to their appropriate dashboard."""
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('dashboard.index'))


@main_bp.route("/sitemap.xml")
def sitemap():
    """Generate a sitemap for SEO."""
    try:
        pages = [
            {"url": url_for('main.index', _external=True), "priority": "1.0"},
            {"url": url_for('main.about', _external=True), "priority": "0.8"},
            {"url": url_for('main.contact', _external=True), "priority": "0.7"},
            {"url": url_for('main.marketplace_insights', _external=True), "priority": "0.6"},
            {"url": url_for('catalog.list_services', _external=True), "priority": "0.9"},
        ]
        
        services = Service.query.filter_by(is_active=True).all()
        for service in services:
            pages.append({
                "url": url_for('catalog.detail', slug=service.slug, _external=True),
                "priority": "0.8",
                "lastmod": service.created_at.strftime("%Y-%m-%d")
            })
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            xml += '  <url>\n'
            xml += f'    <loc>{page["url"]}</loc>\n'
            if "lastmod" in page:
                xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
            xml += f'    <priority>{page["priority"]}</priority>\n'
            xml += '  </url>\n'
        
        xml += '</urlset>'
        
        return xml, 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
        logger.error(f"Error generating sitemap: {e}")
        return "Error generating sitemap", 500


@main_bp.route("/robots.txt")
def robots():
    """Serve robots.txt for search engine crawlers."""
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /dashboard/
Disallow: /cart/
Disallow: /auth/login
Disallow: /auth/register

Sitemap: {url_for('main.sitemap', _external=True)}
"""
    return content, 200, {'Content-Type': 'text/plain'}


@main_bp.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    try:
        db.session.execute("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500


@main_bp.errorhandler(404)
def page_not_found(e):
    """Custom 404 page."""
    return render_template("404.html", year=datetime.now().year), 404


@main_bp.errorhandler(500)
def server_error(e):
    """Custom 500 page."""
    logger.error(f"500 error: {e}")
    return render_template("500.html", year=datetime.now().year), 500


@main_bp.errorhandler(403)
def forbidden(e):
    """Custom 403 page."""
    return render_template("403.html", year=datetime.now().year), 403


@main_bp.route("/set-currency/<code>", methods=["POST"])
def set_currency(code):
    """Switch the displayed currency site-wide (conversion happens client-side;
    stored prices always stay in Naira). Persists to the session and, for
    logged-in users, to their profile so it follows them across devices."""
    from app.models import CurrencyRate
    code = code.upper()
    currency = CurrencyRate.query.filter_by(code=code, is_active=True).first()
    if not currency:
        return {"success": False, "message": "Unknown or inactive currency."}, 400

    session["currency"] = code
    if current_user.is_authenticated:
        current_user.preferred_currency = code
        db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"success": True, "code": code, "symbol": currency.symbol}
    return redirect(request.referrer or url_for("main.index"))


# Context processor for currency switcher (available on every page)
@main_bp.context_processor
def inject_currencies():
    try:
        from app.models import CurrencyRate
        active_currencies = CurrencyRate.query.filter_by(is_active=True).order_by(CurrencyRate.code.asc()).all()
        selected = session.get("currency")
        if not selected and current_user.is_authenticated:
            selected = current_user.preferred_currency
        selected = selected or "NGN"
        if selected not in {c.code for c in active_currencies}:
            selected = "NGN"
        rates_json = {c.code: {"symbol": c.symbol, "rate": c.rate_per_ngn} for c in active_currencies}
        return {
            "active_currencies": active_currencies,
            "selected_currency": selected,
            "currency_rates_json": rates_json,
        }
    except Exception:
        return {"active_currencies": [], "selected_currency": "NGN", "currency_rates_json": {}}


# Context processor for all templates
@main_bp.context_processor
def inject_year():
    """Inject current year into all templates."""
    return {"year": datetime.now().year}


# Context processor for user-related data
@main_bp.context_processor
def inject_user_data():
    """Inject user-related data into all templates."""
    if current_user.is_authenticated:
        try:
            from app.models import CartItem
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
            return {
                "notification_count": 0,
                "cart_count": cart_count
            }
        except:
            return {"notification_count": 0, "cart_count": 0}
    return {"notification_count": 0, "cart_count": 0}
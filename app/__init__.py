import os
from flask import Flask

from app.config import config_map
from app.extensions import db, login_manager, migrate


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    os.makedirs(app.instance_path, exist_ok=True)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.blueprints.main.routes import main_bp
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.catalog.routes import catalog_bp
    from app.blueprints.booking.routes import booking_bp
    from app.blueprints.cart.routes import cart_bp
    from app.blueprints.dashboard.routes import dashboard_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(catalog_bp, url_prefix="/services")
    app.register_blueprint(booking_bp, url_prefix="/book")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Context processor: make company info + cart count available in every template
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = sum(item.quantity for item in current_user.cart_items)
        return {
            "company_name": app.config["COMPANY_NAME"],
            "company_tagline": app.config["COMPANY_TAGLINE"],
            "company_email": app.config["COMPANY_EMAIL"],
            "company_phone": app.config["COMPANY_PHONE"],
            "company_whatsapp": app.config["COMPANY_WHATSAPP"],
            "company_address": app.config["COMPANY_ADDRESS"],
            "company_founded": app.config["COMPANY_FOUNDED"],
            "company_ceo": app.config["COMPANY_CEO"],
            "currency": app.config["CURRENCY_SYMBOL"],
            "cart_count": cart_count,
        }

    # Template filter: convert a stored Naira amount into the shopper's chosen
    # display currency (prices are always stored/computed in Naira; this is
    # purely presentational).
    @app.template_filter("money")
    def money_filter(amount):
        from flask import session
        from flask_login import current_user
        from app.models import CurrencyRate

        amount = amount or 0
        code = session.get("currency")
        if not code and current_user.is_authenticated:
            code = getattr(current_user, "preferred_currency", None)
        code = code or "NGN"

        if code == "NGN":
            return f'{app.config["CURRENCY_SYMBOL"]}{amount:,.2f}'

        rate = CurrencyRate.query.filter_by(code=code, is_active=True).first()
        if not rate:
            return f'{app.config["CURRENCY_SYMBOL"]}{amount:,.2f}'
        converted = amount * rate.rate_per_ngn
        return f'{rate.symbol}{converted:,.2f}'

    # Simple error pages
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("500.html"), 500

    # ── Self-healing schema check ──
    # Normally the Render build step (migrate_db.py) keeps the database schema
    # in sync with the models. This is a safety net in case that step is ever
    # skipped, cached, or fails partway: every time the app process actually
    # starts serving requests, it re-checks its own schema and adds anything
    # missing. It only ever adds columns — never drops or alters data — so
    # it's safe to run unconditionally on every boot.
    with app.app_context():
        try:
            from app.schema_guard import ensure_columns_for
            added = ensure_columns_for(app, db)
            if added:
                app.logger.warning(f"Schema self-heal added missing columns: {added}")
            db.create_all()  # creates any tables that don't exist at all yet (Ad, CurrencyRate, etc.)
        except Exception as e:
            app.logger.error(f"Schema self-heal check failed (app will still start): {e}")

    return app

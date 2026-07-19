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

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(catalog_bp, url_prefix="/services")
    app.register_blueprint(booking_bp, url_prefix="/book")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

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
            "currency": app.config["CURRENCY_SYMBOL"],
            "cart_count": cart_count,
        }

    # Simple error pages
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("500.html"), 500

    return app

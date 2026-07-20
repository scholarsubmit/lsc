import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration. Override secrets via environment variables in production."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-this-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'lsc.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Company info (used across templates)
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Les Starry Corporate")
    COMPANY_TAGLINE = "Print. Brand. Create. Everywhere."
    COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "hello@lsc.com")
    COMPANY_PHONE = os.environ.get("COMPANY_PHONE", "+234 800 000 0000")
    COMPANY_WHATSAPP = os.environ.get("COMPANY_WHATSAPP", "")  # digits only, e.g. 2348001234567 — used for wa.me links
    COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "Aba, Abia State, Nigeria")
    COMPANY_FOUNDED = os.environ.get("COMPANY_FOUNDED", "2019")
    COMPANY_CEO = os.environ.get("COMPANY_CEO", "")  # TODO: set the founder/CEO's real name via env var
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "₦")

    # Booking
    BOOKING_SLOT_MINUTES = 60
    BUSINESS_OPEN_HOUR = 9
    BUSINESS_CLOSE_HOUR = 18

    # Payments (placeholders - wire up real keys when ready)
    PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

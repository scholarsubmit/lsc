# app/config.py
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration."""
    
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-this-in-production")
    
    # ── FIX: Database configuration for Render ──
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        # Render uses postgres://, SQLAlchemy needs postgresql://
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'lsc.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ── FIX: Ensure instance folder exists ──
    try:
        os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    except:
        pass
    
    # Company info
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Les Starry Corporate")
    COMPANY_TAGLINE = "Print. Brand. Create. Everywhere."
    COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "lesstarrycorporate@gmail.com")
    COMPANY_PHONE = os.environ.get("COMPANY_PHONE", "+234 701 517 1362")
    COMPANY_WHATSAPP = os.environ.get("COMPANY_WHATSAPP", "2347015171362")
    COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "Shop 7, 145 Market Road by Adazi, Aba, Abia State, Nigeria")
    COMPANY_FOUNDED = os.environ.get("COMPANY_FOUNDED", "Since 2019")
    COMPANY_CEO = os.environ.get("COMPANY_CEO", "Ogechukwu Sunday Eke")
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "₦")
    
    # Booking
    BOOKING_SLOT_MINUTES = 60
    BUSINESS_OPEN_HOUR = 9
    BUSINESS_CLOSE_HOUR = 18
    
    # Payments
    PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
    
    # ── FIX: Set PREFERRED_URL_SCHEME for HTTPS ──
    PREFERRED_URL_SCHEME = 'https'


class DevelopmentConfig(Config):
    DEBUG = True
    PREFERRED_URL_SCHEME = 'http'


class ProductionConfig(Config):
    DEBUG = False
    # ── FIX: For production on Render ──
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
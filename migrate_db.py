# migrate_db.py
# Standalone entry point for the Render build step (see render.yaml).
# The actual schema-diff logic lives in app/schema_guard.py, shared with
# the automatic startup check in app/__init__.py — so this isn't the only
# safety net if a build step ever gets skipped or fails partway.
#
# Usage: python3 migrate_db.py

from app import create_app
from app.extensions import db
from app.schema_guard import ensure_columns_for


def main():
    app = create_app()
    with app.app_context():
        print("Ensuring columns on existing tables...")
        added = ensure_columns_for(app, db)
        for col in added:
            print(f"  + adding column {col}")
        if not added:
            print("  (schema already up to date)")

        print("Ensuring new tables (Ad, PushSubscription, CurrencyRate, etc.)...")
        db.create_all()
        seed_default_currencies()
    print("Done.")


def seed_default_currencies():
    from app.models import CurrencyRate
    if CurrencyRate.query.count() == 0:
        defaults = [
            ("NGN", "Nigerian Naira", "\u20a6", 1.0),
            ("USD", "US Dollar", "$", 0.00062),
            ("GBP", "British Pound", "\u00a3", 0.00049),
            ("EUR", "Euro", "\u20ac", 0.00057),
        ]
        for code, name, symbol, rate in defaults:
            db.session.add(CurrencyRate(code=code, name=name, symbol=symbol, rate_per_ngn=rate))
        db.session.commit()
        print("  + seeded default currency rates (edit real rates in Admin > Currency)")


if __name__ == "__main__":
    main()

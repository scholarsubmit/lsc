# migrate_db.py
# Idempotent schema upgrade: adds any new columns/tables introduced after the
# original release without needing a full Alembic migration. Safe to run
# every deploy (build step) and every local start — it only ever adds
# missing things, never drops or alters existing data.
#
# Usage: python3 migrate_db.py

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

# table -> [(column_name, DDL_type_clause), ...]
NEW_COLUMNS = {
    "services": [
        ("is_dimensional", "BOOLEAN DEFAULT FALSE"),
        ("price_per_sqft", "FLOAT DEFAULT 0"),
        ("preset_sizes", "TEXT"),
        ("requires_upload", "BOOLEAN DEFAULT FALSE"),
        ("max_upload_mb", "INTEGER DEFAULT 50"),
    ],
}


def ensure_columns(app):
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        for table, columns in NEW_COLUMNS.items():
            if table not in existing_tables:
                continue  # db.create_all() below will create it fresh with all columns
            existing_cols = {c["name"] for c in inspector.get_columns(table)}
            for col_name, ddl_type in columns:
                if col_name in existing_cols:
                    continue
                print(f"  + adding column {table}.{col_name}")
                with db.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {ddl_type}"))


def main():
    app = create_app()
    print("Ensuring columns on existing tables...")
    ensure_columns(app)
    print("Ensuring new tables (Ad, PushSubscription, CurrencyRate, etc.)...")
    with app.app_context():
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

# migrate_db.py
# Idempotent schema upgrade: compares every SQLAlchemy model against the
# actual database schema and adds any columns that exist in the code but
# not yet in the database. This covers old schema drift as well as new
# fields, without needing a full Alembic migration. Safe to run on every
# deploy (build step) and every local start — it only ever adds columns,
# it never drops or alters existing data.
#
# Usage: python3 migrate_db.py

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db


def _ddl_type_for(column, dialect):
    """Best-effort SQL type string for an ALTER TABLE ADD COLUMN, plus a safe
    default clause when the model declares a simple (non-callable) default."""
    try:
        col_type = column.type.compile(dialect=dialect)
    except Exception:
        col_type = "TEXT"

    default_clause = ""
    default = column.default
    if default is not None and getattr(default, "is_scalar", False):
        value = default.arg
        if isinstance(value, bool):
            default_clause = f" DEFAULT {'TRUE' if value else 'FALSE'}"
        elif isinstance(value, (int, float)):
            default_clause = f" DEFAULT {value}"
        elif isinstance(value, str):
            escaped = value.replace("'", "''")
            default_clause = f" DEFAULT '{escaped}'"
        # callables (e.g. datetime.utcnow, generate_reference) can't be
        # expressed as a SQL literal default — new rows still get them from
        # the ORM; existing rows are simply left NULL, which is fine since
        # every nullable-by-necessity field here tolerates that.

    return f"{col_type}{default_clause}"


def ensure_columns(app):
    with app.app_context():
        inspector = inspect(db.engine)
        dialect = db.engine.dialect
        existing_tables = set(inspector.get_table_names())

        for mapper in db.Model.registry.mappers:
            model = mapper.class_
            table = model.__table__
            if table.name not in existing_tables:
                continue  # db.create_all() below creates it fresh with every column

            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                ddl_type = _ddl_type_for(column, dialect)
                print(f"  + adding column {table.name}.{column.name} ({ddl_type})")
                with db.engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl_type}'
                    ))


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

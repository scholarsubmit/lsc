# app/schema_guard.py
"""Self-healing schema check: compares every SQLAlchemy model against the
actual database and adds any column that exists in code but not yet in the
database. Runs both as a standalone script (migrate_db.py, used in the
Render build step) and automatically on every app startup (see
create_app() in app/__init__.py) — so a missed or failed build-step
migration can't leave the live site broken until the next manual fix.

Only ever ADDS columns. Never drops or alters existing data.
"""
import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def _ddl_type_for(column, dialect):
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
        # callable defaults (datetime.utcnow, generate_reference, etc.) can't
        # be expressed as a SQL literal — new rows still get them from the
        # ORM; existing rows are simply left NULL for that column.

    return f"{col_type}{default_clause}"


def ensure_columns_for(app, db):
    """Runs inside an active app context (caller's responsibility)."""
    inspector = inspect(db.engine)
    dialect = db.engine.dialect
    existing_tables = set(inspector.get_table_names())
    added = []

    for mapper in db.Model.registry.mappers:
        table = mapper.class_.__table__
        if table.name not in existing_tables:
            continue  # a fresh table is created with every column by db.create_all()

        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_cols:
                continue
            ddl_type = _ddl_type_for(column, dialect)
            with db.engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl_type}'))
            added.append(f"{table.name}.{column.name}")

    return added

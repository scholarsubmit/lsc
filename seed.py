# seed.py
"""Seeds the database with sample service categories and services.
Standalone entry point for the Render build step — the actual seed data
and logic now live in app/seed_data.py so the exact same code also runs
automatically on every app boot (see create_app() in app/__init__.py) as
a safety net if this build-step script ever gets skipped or fails."""
import os
from app import create_app
from app.extensions import db
from app.seed_data import run_seed

app = create_app(os.environ.get("FLASK_ENV", "development"))


def seed():
    with app.app_context():
        summary = run_seed(app, db, verbose=True)
        print(f"✅ Seed check complete — {summary['services_added']} new service(s), "
              f"{summary['categories_added']} new categor{'y' if summary['categories_added']==1 else 'ies'} added.")
        print("✅ Demo admin login (only created if missing): admin@lsc.com / ChangeMe123!")


if __name__ == "__main__":
    seed()

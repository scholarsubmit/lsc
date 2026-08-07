# seed.py
"""Seeds the database with sample service categories and services."""
import os
from app import create_app
from app.extensions import db
from app.models import ServiceCategory, Service, User
from migrate_db import seed_default_currencies
from app.schema_guard import ensure_columns_for

# Ensure we're using the right environment
app = create_app(os.environ.get("FLASK_ENV", "development"))

CATEGORIES = [
    {
        "name": "Digital Printing",
        "slug": "printing",
        "icon": "printer",
        "description": "Business cards, flyers, banners, large-format & specialty prints.",
    },
    {
        "name": "Branding & Design",
        "slug": "branding",
        "icon": "palette",
        "description": "Logo design, brand identity kits, packaging & marketing collateral.",
    },
    {
        "name": "Photo & Video",
        "slug": "photo-video",
        "icon": "camera",
        "description": "Photo shoots, enlargement, retouching, and video coverage.",
    },
    {
        "name": "Event Planning",
        "slug": "events",
        "icon": "calendar",
        "description": "Consultation, coordination, and full event production.",
    },
]

SERVICES = [
    dict(category="printing", name="Premium Business Cards (Pack of 100)", short="Matte or gloss finish, full colour, thick 350gsm stock.", price=25.00, unit="pack", featured=True),
    dict(category="printing", name="A2 Poster Printing", short="High-resolution large-format poster printing.", price=18.00, unit="item"),
    dict(
        category="printing", name="Flex Banner Printing", short="Weatherproof flex banner, priced per square foot — pick a size or enter your own.",
        price=0.0, unit="sqft", featured=True, is_dimensional=True, price_per_sqft=200.0, requires_upload=True,
        preset_sizes=[
            {"label": "2 x 3 ft", "width_ft": 2, "height_ft": 3},
            {"label": "3 x 5 ft", "width_ft": 3, "height_ft": 5},
            {"label": "4 x 6 ft", "width_ft": 4, "height_ft": 6},
            {"label": "6 x 10 ft", "width_ft": 6, "height_ft": 10},
        ],
    ),
    dict(
        category="printing", name="DI (Direct Impression) Printing", short="Direct-impression printing on rigid boards/materials, priced per square foot.",
        price=0.0, unit="sqft", is_dimensional=True, price_per_sqft=200.0, requires_upload=True,
        preset_sizes=[
            {"label": "2 x 2 ft", "width_ft": 2, "height_ft": 2},
            {"label": "3 x 4 ft", "width_ft": 3, "height_ft": 4},
            {"label": "4 x 8 ft", "width_ft": 4, "height_ft": 8},
        ],
    ),
    dict(category="printing", name="Booklet & Brochure Printing", short="Saddle-stitched booklets, any page count.", price=60.00, unit="job", requires_upload=True),
    dict(category="branding", name="Logo Design Package", short="3 concepts, 2 revisions, full source files.", price=150.00, unit="project", featured=True),
    dict(category="branding", name="Full Brand Identity Kit", short="Logo, colour palette, typography, brand guide.", price=450.00, unit="project"),
    dict(category="branding", name="Product Packaging Design", short="Custom packaging design ready for print.", price=200.00, unit="project"),
    dict(category="photo-video", name="Studio Photo Shoot Session", short="1-hour studio session with edited images.", price=80.00, unit="session", bookable=True, featured=True),
    dict(category="photo-video", name="Photo Enlargement & Printing", short="Museum-quality large-format photo prints.", price=35.00, unit="item"),
    dict(category="photo-video", name="Photo Retouching & Editing", short="Professional colour correction and retouching.", price=15.00, unit="photo"),
    dict(category="photo-video", name="Event Video Coverage (Half Day)", short="Full crew, edited highlight reel included.", price=350.00, unit="event", bookable=True, featured=True),
    dict(category="events", name="Event Consultation (1 hour)", short="Planning session with a dedicated coordinator.", price=50.00, unit="session", bookable=True),
    dict(category="events", name="Full Event Planning & Coordination", short="End-to-end planning: venue, vendors, day-of coordination.", price=800.00, unit="event", bookable=True, featured=True),
    dict(category="events", name="Wedding Photography & Coverage Package", short="Full-day coverage: photos, video, and prints.", price=650.00, unit="event", bookable=True),
]

def slugify(text):
    return text.lower().replace("&", "and").replace(",", "").replace("(", "").replace(")", "").replace("  ", " ").replace(" ", "-")

def seed():
    print("Ensuring schema is up to date...")
    with app.app_context():
        ensure_columns_for(app, db)
        print("Creating tables...")
        db.create_all()
        seed_default_currencies()

        print("Ensuring categories...")
        cat_map = {}
        for c in CATEGORIES:
            cat = ServiceCategory.query.filter_by(slug=c["slug"]).first()
            if not cat:
                cat = ServiceCategory(
                    name=c["name"],
                    slug=c["slug"],
                    icon=c["icon"],
                    description=c["description"]
                )
                db.session.add(cat)
                db.session.flush()
                print(f"  + added category {c['name']}")
            cat_map[c["slug"]] = cat

        print("Ensuring services...")
        import json as _json
        added = 0
        for s in SERVICES:
            slug = slugify(s["name"])
            existing = Service.query.filter_by(slug=slug).first()
            if existing:
                # Backfill print-configurator flags for rows created before these
                # columns existed (e.g. Booklet & Brochure Printing needing uploads).
                if s.get("requires_upload") and not existing.requires_upload:
                    existing.requires_upload = True
                    print(f"  ~ backfilled requires_upload on {existing.name}")
                continue
            svc = Service(
                category_id=cat_map[s["category"]].id,
                name=s["name"],
                slug=slug,
                short_description=s["short"],
                description=s["short"] + " Contact us for bulk pricing and custom specifications.",
                price=s["price"],
                unit=s["unit"],
                is_bookable=s.get("bookable", False),
                is_purchasable=not s.get("bookable", False) or True,
                is_featured=s.get("featured", False),
                estimated_delivery_days=3,
                is_dimensional=s.get("is_dimensional", False),
                price_per_sqft=s.get("price_per_sqft", 0.0),
                preset_sizes=_json.dumps(s["preset_sizes"]) if s.get("preset_sizes") else None,
                requires_upload=s.get("requires_upload", False),
            )
            db.session.add(svc)
            added += 1
            print(f"  + added service {s['name']}")

        # Demo admin account
        if not User.query.filter_by(email="admin@lsc.com").first():
            print("Creating admin account...")
            admin = User(
                full_name="Studio Admin",
                email="admin@lsc.com",
                is_admin=True
            )
            admin.set_password("ChangeMe123!")
            db.session.add(admin)

        db.session.commit()
        print(f"✅ Seed check complete — {added} new service(s) added.")
        print("✅ Demo admin login (only created if missing): admin@lsc.com / ChangeMe123!")

if __name__ == "__main__":
    seed()

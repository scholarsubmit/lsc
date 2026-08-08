# app/seed_data.py
"""Default catalog data + the seeding logic itself.

This is split out from seed.py so the same logic can run two ways:
  1. As the Render build-step script (seed.py), for a clean, verbose,
     one-off run during deploy.
  2. Automatically on every app startup (see create_app() in
     app/__init__.py) — a safety net mirroring schema_guard.py's
     self-healing columns, so a build step that gets skipped, cached,
     or fails partway can never leave a live site with an empty catalog
     until someone notices and re-runs it by hand.

Fully idempotent: every insert is guarded by a "does this already exist"
check, so running it repeatedly (including on every single deploy/boot)
never creates duplicates and never touches data an admin has since edited.
"""
import json as _json
import logging

logger = logging.getLogger(__name__)

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

DEFAULT_CURRENCIES = [
    {"code": "NGN", "name": "Nigerian Naira", "symbol": "₦", "rate_per_ngn": 1.0},
    {"code": "USD", "name": "US Dollar", "symbol": "$", "rate_per_ngn": 0.00062},
    {"code": "GBP", "name": "British Pound", "symbol": "£", "rate_per_ngn": 0.00049},
    {"code": "EUR", "name": "Euro", "symbol": "€", "rate_per_ngn": 0.00057},
]


def slugify(text):
    return text.lower().replace("&", "and").replace(",", "").replace("(", "").replace(")", "").replace("  ", " ").replace(" ", "-")


def run_seed(app, db, verbose=True):
    """Runs inside an active app context (caller's responsibility).
    Safe to call on every boot — every write is guarded by an existence
    check first. Returns a short summary dict for logging."""
    from app.models import ServiceCategory, Service, User, CurrencyRate

    def log(msg):
        if verbose:
            print(msg)

    summary = {"categories_added": 0, "services_added": 0, "currencies_added": 0, "admin_created": False}

    # ── Currencies ──
    for c in DEFAULT_CURRENCIES:
        if not CurrencyRate.query.filter_by(code=c["code"]).first():
            db.session.add(CurrencyRate(**c))
            summary["currencies_added"] += 1
    if summary["currencies_added"]:
        db.session.flush()
        log(f"  + seeded {summary['currencies_added']} default currency rate(s)")

    # ── Categories ──
    cat_map = {}
    for c in CATEGORIES:
        cat = ServiceCategory.query.filter_by(slug=c["slug"]).first()
        if not cat:
            cat = ServiceCategory(name=c["name"], slug=c["slug"], icon=c["icon"], description=c["description"])
            db.session.add(cat)
            db.session.flush()
            summary["categories_added"] += 1
            log(f"  + added category {c['name']}")
        cat_map[c["slug"]] = cat

    # ── Services ──
    for s in SERVICES:
        slug = slugify(s["name"])
        existing = Service.query.filter_by(slug=slug).first()
        if existing:
            if s.get("requires_upload") and not existing.requires_upload:
                existing.requires_upload = True
                log(f"  ~ backfilled requires_upload on {existing.name}")
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
            is_purchasable=True,
            is_featured=s.get("featured", False),
            estimated_delivery_days=3,
            is_dimensional=s.get("is_dimensional", False),
            price_per_sqft=s.get("price_per_sqft", 0.0),
            preset_sizes=_json.dumps(s["preset_sizes"]) if s.get("preset_sizes") else None,
            requires_upload=s.get("requires_upload", False),
        )
        db.session.add(svc)
        summary["services_added"] += 1
        log(f"  + added service {s['name']}")

    # ── Demo admin account (only if no admin exists at all — safe even
    #    after the CEO has changed the password or created their own) ──
    if not User.query.filter_by(is_admin=True).first():
        log("  + creating default admin account (admin@lsc.com)")
        admin = User(full_name="Studio Admin", email="admin@lsc.com", is_admin=True)
        admin.set_password("ChangeMe123!")
        db.session.add(admin)
        summary["admin_created"] = True

    db.session.commit()
    return summary


def run_seed_safely(app, db):
    """Wrapper for automatic startup use — never lets a seeding failure
    crash the app (mirrors ensure_columns_for's error handling)."""
    try:
        summary = run_seed(app, db, verbose=False)
        total = summary["categories_added"] + summary["services_added"] + summary["currencies_added"]
        if total or summary["admin_created"]:
            app.logger.info(f"Startup self-seed: {summary}")
        return summary
    except Exception as e:
        app.logger.error(f"Startup self-seed failed (app will still start): {e}")
        return None

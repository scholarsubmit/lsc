# Changelog — Responsive, Admin Panel & UI Polish Update

This update builds on the deployed `lsc` (Les Starry Corporate) codebase.
Nothing was removed — all existing animations, branding, and pages are
untouched except where noted.

## 1. Admin (CEO) control panel — new
A full admin area at `/admin`, restricted to accounts with `is_admin=True`:

- **Dashboard** (`/admin`) — revenue, order/booking/service counts at a glance,
  plus the 6 most recent orders and bookings.
- **Services & Products** (`/admin/services`) — table of every service with
  its photo, price, active/hidden toggle, and Featured/Bookable flags.
  "Add new service" and "Edit" both include a **photo upload field** — the
  CEO can add a product/service with its own photo directly from the browser,
  no code or FTP access needed.
- **Categories** (`/admin/categories`) — add/delete service categories.
- **Orders** (`/admin/orders`) — every order, filterable by status, with an
  inline dropdown to move an order through pending → paid → processing →
  shipped → completed (or cancelled).
- **Bookings** (`/admin/bookings`) — every booking request, filterable by
  status, with the same inline status control.
- Non-admin users hitting `/admin/*` get a proper **403 page**, not a crash.
- The "Admin panel" link appears in the account dropdown only for admins.

**To make an account an admin:** the seed script already creates
`admin@lsc.com` / `ChangeMe123!` as an admin — change that password
immediately. To promote another account, run:
```bash
python3 -c "
from app import create_app
from app.extensions import db
from app.models import User
app = create_app()
with app.app_context():
    u = User.query.filter_by(email='the-ceo-real-email@example.com').first()
    u.is_admin = True
    db.session.commit()
"
```

## 2. Password visibility toggle
Login and register password fields now have an eye icon that toggles between
hidden and visible text, with proper `aria-label` updates for accessibility.
(`app/static/js/app.js`, `.password-field` / `.password-toggle` in `style.css`)

## 3. Mobile / tablet / desktop responsiveness
- Service and category cards now use `auto-fill`/`minmax` grids instead of
  fixed 3–4 column layouts, so they reflow naturally at any width, dropping
  to a tighter 2-column layout under 620px and 400px.
- Card padding, font sizes, and icon sizes scale down on small screens so
  more fits without feeling cramped (this is the "reduce card size on the
  landing page" request).
- Header/nav height, logo, and button sizing shrink on mobile; the ghost
  "Log in" button hides under 400px to keep the header from crowding.
- All data tables (cart, checkout summary, dashboard orders/bookings, admin
  tables) are wrapped so they scroll horizontally on small screens instead
  of squeezing or breaking.
- Admin layout collapses from a sidebar+content grid to a stacked layout
  with a horizontally-scrollable nav strip under 980px.

## 4. Real product photography
The 6 photos supplied were resized/compressed and wired into the catalog:

| Image | Used for |
|---|---|
| Culinary business cards | "Premium Business Cards" service photo |
| Photoshop/Illustrator/Premiere workspace | "Logo Design Package" service photo |
| Black polo w/ embroidered logo | New "Custom Branded Polo Shirts & Apparel" service |
| "Olori" 50th anniversary flyer | New "Event Flyer & Programme Design" service |
| Camera rig at sunset | "Event Video Coverage (Half Day)" service photo |
| Yellow/black school polos | Homepage "Recent work" gallery |

Service cards on the homepage, catalog list, and detail pages now render
the actual photo when one is set, falling back to the icon placeholder only
for services without a photo yet.

A new horizontally-scrolling **"Recent work"** gallery section was added to
the homepage showing all 6 photos.

## 5. Fun / animated / entertaining touches
- Small confetti burst plays automatically whenever a success message
  flashes (e.g. after checkout or booking) — respects
  `prefers-reduced-motion`.
- Cards lift, scale slightly, and their photo zooms in on hover.
- Category icons wobble on hover; the header logo does a playful tilt.
- Cart badge "pops" in with a spring animation when it updates.
- (Existing CMYK-plate hero animation, scroll-reveal, and stamp animation
  were left as-is — they were already part of the deployed build.)

## Files touched
```
app/blueprints/admin/__init__.py         (new)
app/blueprints/admin/routes.py           (new)
app/templates/admin/_layout.html         (new)
app/templates/admin/dashboard.html       (new)
app/templates/admin/services.html        (new)
app/templates/admin/service_form.html    (new)
app/templates/admin/categories.html      (new)
app/templates/admin/orders.html          (new)
app/templates/admin/bookings.html        (new)
app/templates/403.html                   (new)
app/static/img/services/*.jpg            (new — 6 photos)
app/__init__.py                          (register admin blueprint, 403 handler)
app/templates/base.html                  (admin link in dropdown)
app/templates/auth/login.html            (password toggle)
app/templates/auth/register.html         (password toggle x2)
app/templates/index.html                 (real images, recent-work gallery)
app/templates/catalog/list.html          (real images)
app/templates/catalog/detail.html        (real images)
app/templates/cart/view.html             (responsive table wrapper)
app/templates/dashboard/orders.html      (responsive table wrapper)
app/templates/dashboard/bookings.html    (responsive table wrapper)
app/templates/dashboard/order_detail.html (responsive table wrapper)
app/static/js/app.js                     (password toggle, confetti)
app/static/css/style.css                 (grids, cards, admin, password field, confetti, gallery)
seed.py                                  (image assignments, 2 new services)
```

## Next steps you may want
- Change the demo admin password immediately (`admin@lsc.com` / `ChangeMe123!`).
- Payment gateway and email notifications are still stubbed (see main README).
- Consider adding a lightweight image-cropper on the admin upload form so
  photos come out consistently sized regardless of what's uploaded.

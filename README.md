# Les Starry Corporate — E-commerce & Event Consultation Web App

A full-stack web app for a digital printing, branding, and event consultation
business. Customers can browse services, buy print products, book sessions
(photo shoots, video coverage, event consultations), and track orders —
all from a purple/white branded storefront that installs like a native app.

**Stack:** Python (Flask) backend · HTML/CSS/JavaScript frontend · SQLite
(swap for Postgres/MySQL anytime) · installable PWA (works offline-ish and
can be "downloaded" straight from the browser, no app store needed).

---

## 1. What's included

| Feature                                                            | Where                                                      |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| Service catalog (printing, branding, photo/video, events)          | `app/blueprints/catalog`                                   |
| Booking system (date/time, location, event type, notes)            | `app/blueprints/booking`                                   |
| Shopping cart + checkout → orders                                  | `app/blueprints/cart`                                      |
| Accounts (register/login/logout)                                   | `app/blueprints/auth`                                      |
| Customer dashboard (orders + bookings history)                     | `app/blueprints/dashboard`                                 |
| Reviews & star ratings per service                                 | `app/blueprints/catalog` (`add_review`)                    |
| Light/dark theme switcher (persisted)                              | `app/static/js/theme.js`                                   |
| Installable PWA (manifest, service worker, offline page, icons)    | `app/static/manifest.json`, `app/static/service-worker.js` |
| "Marketplace insights" page (Jumia/Alibaba/Temu-inspired UX notes) | `/marketplace-insights`                                    |

Sample data: 4 categories, 14 services (business cards, banners, logo
design, photo shoots, event planning, etc.) via `seed.py`.

---

## 2. Run it locally

```bash
# 1. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database and load sample services
python3 seed.py

# 4. Run the app
python3 run.py
```

Visit **http://127.0.0.1:5000**. A demo admin account is created by the
seed script: `admin@lsc.com` / `ChangeMe123!` — change this
password immediately if you keep it.

To reset the database, delete `instance/lsc.db` and re-run `seed.py`.

---

## 3. Project structure

```
lsc/
├── app/
│   ├── __init__.py            # App factory, blueprint registration
│   ├── config.py              # Settings (reads from environment variables)
│   ├── extensions.py          # SQLAlchemy, Flask-Login, Flask-Migrate
│   ├── models.py              # User, Service, Booking, Order, Review, Cart...
│   ├── blueprints/
│   │   ├── auth/               # register / login / logout
│   │   ├── main/               # home, about, contact, marketplace-insights
│   │   ├── catalog/             # service listing, detail, reviews
│   │   ├── booking/             # scheduling for bookable services
│   │   ├── cart/                # add/update/remove, checkout → order
│   │   └── dashboard/           # customer's own orders & bookings
│   ├── templates/              # Jinja2 HTML templates (all pages)
│   └── static/
│       ├── css/style.css       # design tokens + all component styles
│       ├── js/                 # theme.js, app.js, pwa.js
│       ├── manifest.json       # PWA manifest
│       ├── service-worker.js   # offline cache + install support
│       └── icons/               # generated app icons
├── generate_icons.py           # regenerates app icons (Pillow, no external art)
├── seed.py                     # sample categories/services + demo admin
├── run.py                      # entry point
├── requirements.txt
└── .env.example                # copy to .env and fill in for production
```

---

## 4. Design system (why it looks the way it does)

- **Colors:** deep purple `#5B21B6` primary, violet `#8B5CF6` accent, white
  and soft-lavender backgrounds in light mode; near-black `#120E1A` with the
  same violet accent in dark mode — defined as CSS custom properties in
  `style.css`, so retheming is a matter of changing a handful of variables.
- **Type:** Sora (headings), Inter (body), IBM Plex Mono (prices, job/booking
  reference codes — a nod to real print-shop job tickets).
- **Signature motif:** corner "registration marks" (the crosshair marks
  printers use to align color plates) appear on hero panels and cards —
  a detail pulled from the print industry itself rather than a generic
  gradient or icon.
- **Theme switcher:** toggle in the header; choice is saved to
  `localStorage` and falls back to the visitor's OS-level light/dark
  preference on first visit.

---

## 5. Making it "downloadable" (PWA)

The app ships as an installable Progressive Web App:

- `app/static/manifest.json` declares the app name, icons, and colors.
- `app/static/service-worker.js` caches core assets and serves an offline
  fallback page, which is what qualifies the site for the browser's
  "Install app" / "Add to Home Screen" prompt.
- `app/static/js/pwa.js` wires up the install button in the footer.

**Requirement:** PWAs only install from HTTPS (or `localhost`) origins.
Once deployed to a real domain with SSL, visitors on Chrome/Edge/Android
will see an install prompt automatically; iOS Safari users can use
"Share → Add to Home Screen."

To refresh the icons (e.g. with your real logo), replace the artwork in
`app/static/icons/` or edit `generate_icons.py` and re-run it.

---

## 6. Extending toward a full production build

This is a real, running foundation — not a mockup — but a few things are
intentionally left as next steps so you can plug in your own business
details and accounts:

- **Payments:** `payment_method` is captured at checkout but no gateway is
  wired up yet. Add Stripe or Paystack (keys are already stubbed in
  `.env.example` / `config.py`) inside `app/blueprints/cart/routes.py`.
- **Email notifications:** booking/order confirmations currently just flash
  a message in the browser. Add Flask-Mail or a transactional email API
  (SendGrid, Postmark) in the `checkout()` and `new_booking()` view
  functions.
- **Admin panel:** there's an `is_admin` flag on `User` and a demo admin
  account, but no admin UI yet — Flask-Admin or a custom dashboard is a
  natural next addition for managing services, bookings, and orders.
- **Image uploads:** services currently reference a placeholder image path;
  wire up real product/service photos via a file upload field + storage
  (local disk, S3, or Cloudinary).
- **Marketplace listings (Jumia/Alibaba/Temu):** these platforms don't offer
  public APIs for arbitrary third-party storefronts to resell through — see
  `/marketplace-insights` in the app for what was borrowed from their UX
  instead. If you want an actual presence there, that's a separate seller
  registration per platform.

---

## 7. Deploying

For production:

1. Set `FLASK_ENV=production` and a strong random `SECRET_KEY` (see
   `.env.example`).
2. Point `DATABASE_URL` at a real database (Postgres recommended).
3. Serve with a WSGI server, e.g.:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 run:app
   ```
4. Put it behind Nginx/Caddy with HTTPS — required for the PWA install
   prompt and for safe login sessions.
5. Any static host + reverse proxy (Render, Railway, a VPS with Nginx, etc.)
   will work — there's nothing platform-specific in the code.

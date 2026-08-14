# SmartCity — Civic Issue Reporting & Resolution Platform

Citizens report civic problems (potholes, streetlights, garbage, water leaks…) by pinning them on a map with a photo. The city administration sees every real-world problem exactly once — deduplicated, routed to the right department, and prioritised — then works it through a tracked lifecycle until the reporter confirms the fix.

Two purpose-built interfaces share one backend:

- **Citizen portal** (light theme) — a simple, phone-friendly reporting flow with live status tracking and a public city map.
- **Admin command center** (dark theme) — a data-dense dashboard with a prioritised work queue, a live city map, and analytics computed from the real database.

---

## Requirement coverage

| # | Requirement | Where it lives |
|---|---|---|
| 1 | Two-role auth & RBAC | JWT cookie auth; `require_roles` dependency guards every endpoint on the backend (`app/core/dependencies.py`), `RoleRoute` guards the frontend routes |
| 2 | Map-based reporting | `ReportIssue` wizard: map pin + GPS, category grid, description, photo upload ([maps API choice](#maps--geolocation-api)) |
| 3 | Duplicate detection | Custom algorithm in `app/services/citizen.py` — see [How duplicate detection works](#how-duplicate-detection-works) |
| 4 | Automated department routing | Data-driven `category_routes` table (`app/services/routing.py`) — add a category or department with a DB row, no code change |
| 5 | Issue lifecycle | Status workflow + full status history, admin resolution notes & proof photos, citizen confirm/reopen |
| 6 | Interactive city map | `CityMap` component — live markers color-coded by status *or* category, for both roles |
| 7 | Admin analytics | `/api/admin/analytics` computes category/status/department splits, avg resolution time, department comparison, and hotspots from the live database |
| 8 | Database integration | PostgreSQL via SQLAlchemy + Alembic migrations: users, issues, locations, status history, departments, routes, notifications, resolution evidence |
| 9 | Responsive, clean UI | Mobile-first CSS, responsive breakpoints across both portals |
| 10 | Error handling | GPS denial fallback, photo validation (type/size/magic bytes), geocoding failure fallback to coordinates, network error states with retry everywhere |

### Beyond the brief

| Feature | How it works |
|---|---|
| **SLA-based escalation** | Every category has an SLA (2 days for garbage overflow … 10 for damaged property, `app/core/issue_types.py`). An idempotent sweep runs on every admin load: open cases past their deadline are flagged, logged in their status history, boosted ×1.5 in the priority queue with an "⚠ SLA breached" badge, and the higher authority (General Administration) gets a notification. |
| **Citizen upvoting** | Citizens support existing problems straight from the city map popups (`POST /citizen/issues/{id}/vote`, toggleable). Reporters of a case can't double-dip — their report already counts. Votes add to the "people affected" factor of the priority score, so high-impact problems rise in the department queues. |
| **Public transparency score** | `GET /api/public/transparency` — **no login required** — computes a 0–100 score and A+–D grade per department: 50% resolution rate + 30% resolved-within-SLA + 20% speed vs a 14-day baseline. Rendered at `/transparency` as a public report card, linked from the login page and the citizen footer. |
| **Multi-language reporting** | A language switcher (🌐) in the citizen portal flips the entire reporting experience — navigation, category names and hints, the 5-step wizard, statuses, timeline, and lifecycle updates — between English and हिन्दी, persisted per device. Free-text reports accept any script; adding another regional language is one dictionary in `frontend/src/shared/i18n.jsx`. |
| **AI photo verification** | With an `ANTHROPIC_API_KEY` configured, every uploaded report photo is checked by Claude vision against the reported category ("does this actually look like a pothole?"), and every proof-of-resolution photo against "does this show the issue fixed?". Verdicts run as background tasks (submission never blocks), are stored on the issue, and surface as 🤖 badges in the admin queue and on the citizen's report page. Without a key, photos are simply marked unverified — nothing breaks. `app/services/photo_verification.py`. |

---

## Maps & Geolocation API

**What we use**

| Concern | Choice |
|---|---|
| Map rendering | [Leaflet 1.9](https://leafletjs.com/) via [React-Leaflet 5](https://react-leaflet.js.org/) |
| Base tiles (citizen, light) | OpenStreetMap standard raster tiles |
| Base tiles (admin, dark) | CARTO *Dark Matter* tiles (OSM data) |
| Reverse geocoding | [OSM Nominatim](https://nominatim.org/) `reverse` API |
| Device location | Browser Geolocation API (`navigator.geolocation`) |

**Why we chose it**

We evaluated three options:

- **Google Maps Platform** — best-in-class data, but needs an API key with billing enabled, has restrictive caching/usage terms, and locks the project to one vendor.
- **Mapbox GL JS** — beautiful vector tiles, but again API-key + quota-bound, and a much heavier bundle.
- **Leaflet + OpenStreetMap** *(chosen)* — completely free and key-less (nothing to leak, nothing to bill), open data, a ~42 KB library with mature React bindings, and provider-agnostic: any XYZ tile server can be swapped in via env config (which is exactly how the admin map uses CARTO's dark tiles). Nominatim gives us reverse geocoding on the same open dataset.

Trade-offs we accepted: OSM raster tiles are less polished than Google/Mapbox vector maps, and public Nominatim has fair-use rate limits — fine at this scale, and both are swappable behind env vars (`VITE_MAP_TILE_URL`, `VITE_MAP_TILE_URL_DARK`, `VITE_GEOCODING_URL`) if the city later pays for a commercial provider.

**How it's integrated** (all in `frontend/src`)

- `citizen/components/LocationPicker.jsx` — reporting step 2: tap-to-pin, draggable marker, "Use my current location" (Geolocation API with denial/timeout fallback messaging), and debounced/abortable reverse geocoding that fills the address automatically. If geocoding fails, coordinates are used — the report never blocks on a third-party service.
- `shared/components/CityMap.jsx` — the live city map both roles share: one emoji marker chip per case with a color ring (status or category mode), popups with case details, auto `fitBounds`, and a legend computed from what's actually on screen.
- `citizen/components/IssueLocationMap.jsx` — static mini-map on the report detail page.

---

## Architecture

```
frontend/  React 19 + Vite + React Router 7 + react-leaflet   (JWT cookie auth)
backend/   FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL      (service-layer architecture)
           app/api/       thin routers (auth, citizen, admin)
           app/services/  domain logic (citizen, admin, routing, lifecycle, city_map, notification)
           app/models.py  User, Issue, StatusHistory, Department, CategoryRoute, Notification
```

### How duplicate detection works

When a report is submitted (`app/services/citizen.py`):

1. Per-category **radius** (25 m for a pothole … 80 m for water leakage) and **recency window** (3 days for garbage … 60 days for potholes) come from `app/core/issue_types.py`.
2. A degree-space bounding box around the new pin is searched for an **open case** of the same category inside the window.
3. Match → the report is **linked as a member of the existing case** (it keeps its own tracking ID, the reporter still sees their own report; the case's citizen count grows, boosting priority). No match → the report becomes a new case's **primary**.

Members inherit the case's *effective status*, so when an admin resolves the case, every reporter of that pothole sees "Resolved".

### Lifecycle & status history

Every transition is recorded in the `status_history` table (who — citizen or admin, old → new status, note, optional photo). Admins add **resolution notes** and upload **proof-of-resolution photos**; reporters see the full activity trail and, once a case is resolved, can **confirm the fix** or **reopen** the whole case if the problem persists.

### Priority & analytics

The work queue orders cases by `severity-weight × citizens-affected × (1 + days-open / 7)`. The analytics endpoint aggregates live data: splits by category/status/department, average resolution time (overall + per department), and **hotspots** — ~110 m map cells accumulating 2+ reports.

---

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows   (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env            # then set DATABASE_URL + JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Create an administrator account:

```bash
python -m scripts.create_admin admin@city.gov <password>
```

### Frontend

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173, proxies /api to :8000
```

### Tests

```bash
cd backend && pytest              # 101 tests: auth/RBAC, duplicates, routing, lifecycle, analytics
cd frontend && npm test           # 54 tests: reporting flow, dashboards, maps, lifecycle UI
```

---

## API

See [api-documentation.md](api-documentation.md) for the full endpoint reference.

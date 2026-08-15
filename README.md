# 🏙 SmartCity — Civic Issue Reporting & Resolution Platform

### 🔗 Live demo — **[smartcity-y1bu.onrender.com](https://smartcity-y1bu.onrender.com/)**

*Hosted on Render's free tier, which sleeps after 15 minutes idle — the first visit can take up to a minute to wake. Everything after that is instant.*

---

> **Report it once. Track it live. Hold the city accountable.**

Citizens pin civic problems — potholes, dead streetlights, overflowing bins, water leaks — on a map with photo evidence. The administration sees every real-world problem **exactly once** (deduplicated automatically), routed to the right department, ranked by real impact, escalated when it sits too long, and worked through a fully audited lifecycle until the **reporter themselves confirms the fix**. A public report card scores every department on how well they actually deliver.

[![Live](https://img.shields.io/badge/live-smartcity--y1bu.onrender.com-success)](https://smartcity-y1bu.onrender.com/) ![Backend tests](https://img.shields.io/badge/backend_tests-110_passing-brightgreen) ![Frontend tests](https://img.shields.io/badge/frontend_tests-59_passing-brightgreen) ![Stack](https://img.shields.io/badge/FastAPI_·_React_19_·_PostgreSQL-0b1029) ![Deploy](https://img.shields.io/badge/deploy-Docker_·_Render-2496ED) ![Languages](https://img.shields.io/badge/English_+_हिन्दी-orange) ![AI](https://img.shields.io/badge/AI_photo_verification-Claude_vision-8A2BE2)

---

## 🏗 Architecture

Every layer below is real, tested code in this repository — the diagram source lives in [`docs/architecture.mmd`](docs/architecture.mmd).

![SmartCity architecture](architecture-diagram.png)

**How a report flows through the system:**

```mermaid
sequenceDiagram
    autonumber
    actor C as 📱 Citizen
    participant API as 🚀 FastAPI
    participant DUP as 🔁 Duplicate detection
    participant AI as 🤖 Claude vision
    participant D as 🏛 Department
    actor A as 🖥 Admin

    C->>API: Pin location + category + photo + description
    API->>DUP: Same category, ~same spot, recent?
    alt existing open case nearby
        DUP-->>API: Link as member of case (no new case)
    else new problem
        DUP-->>API: New case → auto-route by category
        API->>D: 📧 Notify department inbox + email
    end
    API-->>C: Tracking ID (SMC-2026-XXXXXX)
    API--)AI: background: does photo match category?
    AI--)API: 🤖 verdict stored on the issue

    A->>API: Work queue (priority = severity × people × age)
    Note over API: SLA sweep — overdue cases escalate<br/>to higher authority + 1.5× priority
    A->>API: Status → Resolved + note + proof photo
    API--)AI: background: does proof show the fix?
    API-->>C: Full status history + resolution evidence
    C->>API: ✅ Confirm fix — or ↩ reopen the whole case
```

---

## ⚡ The features that make it powerful

> 📘 **Want the exact rules?** [`docs/FUNCTIONALITY.md`](docs/FUNCTIONALITY.md) is the full functional specification — every threshold, formula, state transition and edge case, with worked examples and the defining source file for each.

### 🔁 One problem = one case (custom duplicate detection)
Fifteen people reporting the same pothole doesn't create fifteen tickets. Each new report is checked against **per-category geographic radii** (25 m for a pothole … 80 m for a water leak) and **recency windows** (3–60 days) — a match links the report into the existing case, and every reporter still tracks it under their own ID. The citizen count then *boosts* the case's priority, so mass-reported problems rise to the top instead of clogging the queue.

### ⏰ SLA escalation — nothing rots in a queue
Every category has a service-level limit (2 days for garbage overflow … 10 for damaged property). An idempotent sweep runs on every admin load: breached cases get flagged **⚠ SLA breached**, boosted ×1.5 in priority, logged in their audit trail, and General Administration — the higher authority — is notified automatically.

### 🤖 AI photo verification (Claude vision)
Every uploaded report photo is checked in the background against the claimed category — *"does this actually look like a pothole?"* — and every proof-of-resolution photo against *"does this show the issue fixed?"*. Verdicts surface as badges in the admin queue with a one-sentence reason. No API key? The system degrades gracefully to unverified. Submissions never block on AI.

### 🏆 Public transparency report card
`/transparency` needs **no login**. Every department gets a live 0–100 score and an A+–D grade from three weighted signals — resolution rate (50 %), resolved-within-SLA rate (30 %), and speed vs a 14-day baseline (20 %) — computed straight from the database on every request. Nobody curates it; the methodology is printed on the page.

### 🗺 Live city map with citizen upvoting
Every active case is an emoji pin, color-coded by **status or category** (toggle), with popups showing report counts, department, and tracking ID. Citizens **upvote** problems that affect them straight from the popup — reporters can't double-dip on their own case — and votes feed directly into the priority formula departments work from.

### 🔄 A lifecycle that closes the loop
Every transition is recorded in an immutable **status history** — who (citizen or administration), old → new status, note, photo, timestamp. Admins attach resolution notes and proof photos; reporters see the full trail and get the last word: **"Yes, it's fixed"** or **"No, reopen it"** — and reopening a duplicate reopens the *whole case* for everyone.

### 🌐 Bilingual, phone-first
A 🌐 switcher flips the entire citizen experience — navigation, the 5-step wizard, categories, statuses, timeline, lifecycle updates — between **English and हिन्दी**, persisted per device. Adding another regional language is one dictionary file. Everything is responsive down to a 375 px phone, because citizens report from the street.

### 📊 Analytics computed live, drawn by hand
The admin analytics tab is 100 % real aggregation — category/status/department splits, average resolution time, department comparison, and **hotspot detection** (~110 m grid cells that keep collecting reports). Charts are hand-built SVG with a palette validated for color-vision deficiency on the dark surface — no chart library, no fake numbers.

### 🛡 Security that isn't just hidden buttons
Role-based access control is enforced **on the backend** — every admin endpoint rejects citizens with 403 and vice versa, covered by tests. Uploads are validated by magic bytes (not just extensions), JWTs live in HTTP-only cookies, and passwords are bcrypt-hashed.

---

## 🗺 Maps & Geolocation API — what we chose and why

| Concern | Choice |
|---|---|
| Map rendering | [Leaflet 1.9](https://leafletjs.com/) via [React-Leaflet 5](https://react-leaflet.js.org/) |
| Base tiles (citizen, light) | OpenStreetMap standard raster tiles |
| Base tiles (admin, dark) | CARTO *Dark Matter* tiles (OSM data) |
| Reverse geocoding | [OSM Nominatim](https://nominatim.org/) `reverse` API |
| Device location | Browser Geolocation API |

**Why.** We evaluated three options: **Google Maps Platform** (best data, but API key + billing + restrictive caching terms), **Mapbox GL JS** (beautiful vector tiles, but key-bound and a heavy bundle), and **Leaflet + OpenStreetMap** — which we chose: completely free and key-less (nothing to leak, nothing to bill), open data, a ~42 KB library with mature React bindings, and provider-agnostic — any XYZ tile server swaps in via env config, which is exactly how the admin map uses CARTO's dark tiles. Nominatim adds free reverse geocoding on the same open dataset. Trade-offs accepted: raster tiles are less polished than vector maps, and public Nominatim has fair-use rate limits — both swappable behind `VITE_MAP_TILE_URL` / `VITE_MAP_TILE_URL_DARK` / `VITE_GEOCODING_URL` if the city later pays for a commercial provider.

**How it's integrated** (all under `frontend/src`):

- `citizen/components/LocationPicker.jsx` — reporting step 2: tap-to-pin, draggable marker, **"Use my current location"** (with denial/timeout fallback messaging), and abortable reverse geocoding that auto-fills the address. If geocoding fails, coordinates are used — a report never blocks on a third-party service.
- `shared/components/CityMap.jsx` — the shared live map: one emoji marker chip per case with a colored ring (status or category mode), vote buttons, auto `fitBounds`, and a legend computed from what's actually on screen.
- `citizen/components/IssueLocationMap.jsx` — static mini-map on each report's detail page.

---

## ✅ Requirement coverage

| # | Requirement | Where it lives |
|---|---|---|
| 1 | Two-role auth & backend-enforced RBAC | `app/core/dependencies.py` (`require_roles`), `RoleRoute` on the frontend |
| 2 | Map-based reporting (pin + category + photo + description) | `ReportIssue` wizard + [maps section](#-maps--geolocation-api--what-we-chose-and-why) |
| 3 | Duplicate detection (own algorithm) | `app/services/citizen.py` — radius + recency case grouping |
| 4 | Automated department routing (extensible) | `category_routes` table — add a category with a DB row, zero code |
| 5 | Issue lifecycle & status workflow | Status history, resolution notes & proof, citizen confirm/reopen |
| 6 | Interactive city map | `CityMap` — color-coded live markers for both roles |
| 7 | Admin analytics dashboard (real data) | `/api/admin/analytics` — splits, avg resolution, comparison, hotspots |
| 8 | Database integration | PostgreSQL · SQLAlchemy 2 · 7 Alembic migrations — users, issues, locations, history, departments, votes, evidence |
| 9 | Responsive, purpose-built UIs | Light phone-first citizen portal vs dark data-dense admin |
| 10 | Error handling | GPS denial, upload validation (type/size/magic bytes), geocoding fallback, retryable error states |

**Beyond the brief:** SLA escalation · citizen upvoting · public transparency score · multi-language (EN/हिन्दी) · AI photo verification — all detailed [above](#-the-features-that-make-it-powerful).

---

## 🚀 Getting started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env            # set DATABASE_URL + JWT_SECRET_KEY (ANTHROPIC_API_KEY optional)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Create an administrator:

```bash
python -m scripts.create_admin admin@city.gov <password>
```

### Frontend

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 — proxies /api to :8000
```

### Tests

```bash
cd backend && pytest              # 110 tests — auth/RBAC, duplicates, routing, lifecycle, SLA, votes, transparency, AI verification
cd frontend && npm test           # 59 tests — wizard, dashboards, maps, lifecycle UI, i18n, badges
```

---

## 🐳 Deployment

**Live at [smartcity-y1bu.onrender.com](https://smartcity-y1bu.onrender.com/)** — one
Docker container serving the React app and the API from a single origin, backed by
managed PostgreSQL.

The container is self-sufficient: it waits for the database, applies every
migration, provisions the first administrator if you asked for one, and then
serves the app. There is no manual setup step, on any host.

### Two images, two jobs

| Image | Serves | Use it for |
|---|---|---|
| [`Dockerfile`](Dockerfile) | React app **+** API, one origin | Production — this is what Render builds |
| [`backend/Dockerfile`](backend/Dockerfile) | API only | Running the backend alone, or a separately-hosted frontend |

The frontend is bundled into the API container on purpose. The auth cookie is
`SameSite=Lax`, so a frontend on a *different* origin could not send it and every
request would arrive unauthenticated. Same origin, no CORS, no cookie problems.

### Deploy to Render

[`render.yaml`](render.yaml) is a complete blueprint — a web service plus a
PostgreSQL database, already wired together.

1. Render Dashboard → **New +** → **Blueprint** → pick this repository
2. Enter `ADMIN_EMAIL` and `ADMIN_PASSWORD` (8+ characters) when prompted
3. **Apply**

`DATABASE_URL` is injected from the database and `JWT_SECRET_KEY` is generated by
Render, so there are no secrets to copy by hand. Every push to `main` redeploys
automatically.

On the free tier the service sleeps after 15 minutes idle, and uploaded photos are
lost on redeploy because the filesystem is ephemeral — reports and accounts live in
PostgreSQL and survive. The commented-out `disk:` block in `render.yaml` makes
uploads persistent on a paid plan.

### Run the whole stack locally

`docker-compose.yml` brings up PostgreSQL and the API together:

```bash
docker compose up --build
```

The API is then on <http://localhost:8000> — interactive docs at `/docs`,
liveness probe at `/healthz`.

Copy `.env.example` to `.env` first to set real values. At minimum set
`JWT_SECRET_KEY`; set `ADMIN_EMAIL` and `ADMIN_PASSWORD` too and the first
admin account is created on startup, which is how you get in on hosts that
give you no shell.

### Or build an image directly

```bash
docker build -t smartcity ./          # full app: React + API
```

```bash
docker build -t smartcity-api ./backend   # API only
```

Point `DATABASE_URL` at any PostgreSQL instance and run it. `postgres://` and
`postgresql://` URLs — the format managed providers hand out — are rewritten to
the psycopg 3 driver automatically, so you can paste the provider's URL as-is.

### What the image does for you

| Behaviour | Why it matters |
|---|---|
| Waits up to 60s for the database | Containers start in parallel with their database, and managed Postgres can drop connections during failover |
| Applies migrations on every boot | A redeploy is never out of step with the schema |
| Runs as a non-root user (uid 10001) | Nothing in the container runs with more privilege than it needs |
| `HEALTHCHECK` against `/healthz` | Orchestrators can tell a wedged container from a live one |
| Idempotent startup | Restarts and redeploys are safe: migrations no-op, admin bootstrap skips an existing account |

### Configuration

Every variable is documented in [`.env.example`](.env.example). The ones that
matter most in production:

| Variable | Notes |
|---|---|
| `JWT_SECRET_KEY` | **Required.** Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Defaults to the bundled `db` service under Compose |
| `DEBUG` | Keep `false` — it is what marks the auth cookie `Secure` |
| `CORS_ORIGINS` | Browser origins allowed to call the API |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Optional first administrator, created on startup |
| `ANTHROPIC_API_KEY` | Optional; without it photos are marked `UNVERIFIED` |

### One thing to plan for

**Uploaded photos are files, not rows.** Compose keeps them in the `uploads`
volume. On a host with an ephemeral filesystem — including Render's free tier —
mount a persistent disk at `/app/uploads` or move `app/core/storage.py` to
object storage. Everything else lives in PostgreSQL and survives on its own.

---

## 📚 Documentation

| Document | Contents |
|---|---|
| **[docs/FUNCTIONALITY.md](docs/FUNCTIONALITY.md)** | **Full functional specification** — 25 sections covering permissions, the category constants table, the duplicate-detection algorithm, priority & transparency formulas (with worked examples), the lifecycle state machine, hotspot detection, the error-handling catalogue, and the data model |
| [api-documentation.md](api-documentation.md) | Endpoint reference — auth, citizen, admin, public |
| [docs/architecture.mmd](docs/architecture.mmd) | Editable Mermaid source of the architecture diagram |
| [docs/er-diagram.mmd](docs/er-diagram.mmd) | Entity-relationship diagram of the database schema |
| [render.yaml](render.yaml) | Deployment blueprint — web service + managed PostgreSQL |
| [`.env.example`](.env.example) | Deployment configuration, annotated |
| `backend/.env.example` | Local development configuration, annotated |

**Quick links into the spec:** [duplicate detection](docs/FUNCTIONALITY.md#6-duplicate-detection--case-grouping) · [priority scoring](docs/FUNCTIONALITY.md#8-priority-scoring) · [SLA escalation](docs/FUNCTIONALITY.md#9-sla-escalation) · [lifecycle](docs/FUNCTIONALITY.md#11-issue-lifecycle--status-workflow) · [transparency scoring](docs/FUNCTIONALITY.md#20-public-transparency-scoring) · [error handling](docs/FUNCTIONALITY.md#23-error-handling-catalogue) · [data model](docs/FUNCTIONALITY.md#24-data-model)

**Tech stack:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Pydantic v2 · React 19 · Vite · React Router 7 · react-leaflet · Anthropic Claude API (vision) · pytest · Vitest + Testing Library.

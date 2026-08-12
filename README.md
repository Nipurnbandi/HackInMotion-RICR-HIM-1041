# Hack

Full-stack app with JWT auth, two-role RBAC (CITIZEN / ADMIN), and PostgreSQL.

**No Docker** — you install and run PostgreSQL manually on your machine.

---

## Your PostgreSQL setup

Detected on your machine:

| Item | Value |
|------|-------|
| **Install path** | `C:\Program Files\PostgreSQL\18` |
| **Version** | PostgreSQL 18 |
| **Database** | `hack` |
| **Connection** | set in `backend/.env` → `DATABASE_URL` |

`psql` path:

```text
C:\Program Files\PostgreSQL\18\bin\psql.exe
```

1. Download from https://www.postgresql.org/download/windows/
2. Run the installer (PostgreSQL 16 recommended)
3. Remember the **password** you set for the `postgres` superuser
4. Keep default port **5432**
5. Finish install — PostgreSQL service should be running

Check it's running: open **Services** → look for `postgresql-x64-16` (Running)

---

## 2. Create the database (manual)

Open **SQL Shell (psql)** from Start Menu, or **pgAdmin**.

Connect as `postgres`, then run:

```sql
CREATE DATABASE hack;
```

Optional — dedicated app user:

```sql
CREATE USER hackuser WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE hack TO hackuser;
```

---

## 3. Configure the app

```bash
cd backend
copy .env.example .env
```

Edit `backend/.env` — set your real Postgres password:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/hack
```

Format:

```text
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE
```

---

## 4. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.create_admin admin@example.com YourSecurePassword
uvicorn app.main:app --reload
```

`alembic upgrade head` creates these tables in Postgres:

| Table | Columns |
|-------|---------|
| `users` | id, email, hashed_password, role, created_at, updated_at |
| `issues` | id, tracking_id, citizen_id, title, category, description, latitude, longitude, address, photo_url, status, case_id, is_primary, created_at, updated_at |

**Duplicate detection (silent):** when a new report matches an open report of
the same category within ~50 m from the last 7 days, it silently joins that
report's `case_id` instead of opening a new case (`is_primary = false`). The
citizen is never told; their report keeps its own tracking ID and appears in
My Reports as usual, but its displayed status is read from the case's primary
report. Admin lists and counts show primaries only — one row per real problem.

`issues.status` is one of `SUBMITTED`, `UNDER_REVIEW`, `IN_PROGRESS`, `RESOLVED`,
`REJECTED`. `issues.category` is one of `STREETLIGHT`, `POTHOLE`,
`GARBAGE_OVERFLOW`, `WATER_LEAKAGE`, `DAMAGED_PUBLIC_PROPERTY`,
`ILLEGAL_DUMPING`, `BROKEN_DRAINAGE`.

Photo evidence is written to `backend/uploads/issues/` (git-ignored) and served
at `/uploads/...`; only the path is stored in Postgres. Swap
`backend/app/core/storage.py` for an S3-compatible backend without touching the
`Issue` model.

---

## 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000/docs  
- App: http://localhost:5173  

### Map configuration

The citizen report form uses **Leaflet with OpenStreetMap tiles and Nominatim
reverse geocoding — no API key is required**, so it works out of the box.

To point at a different provider, set these in `frontend/.env` (all optional):

```env
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_MAP_TILE_ATTRIBUTION=&copy; OpenStreetMap contributors
VITE_GEOCODING_URL=https://nominatim.openstreetmap.org/reverse
```

Never commit a provider key. If reverse geocoding is unavailable the form still
works — the report is saved with latitude/longitude and no address.

---

## View data in PostgreSQL

**pgAdmin** (installed with Postgres):
1. Servers → PostgreSQL → Databases → hack → Schemas → public → Tables

**psql:**

```bash
psql -U postgres -d hack
\dt
SELECT id, email, role FROM users;
\q
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` | Start PostgreSQL service in Windows Services |
| `password authentication failed` | Fix password in `.env` `DATABASE_URL` |
| `database "hack" does not exist` | Run `CREATE DATABASE hack;` in psql |
| `alembic` errors on re-run | DB may already be migrated — check `\dt` in psql |

---

## Tests

Unit tests use in-memory SQLite (no Postgres needed for pytest):

```bash
cd backend
.venv\Scripts\pytest -v
```

Frontend tests (Vitest + Testing Library):

```bash
cd frontend
npm test
```

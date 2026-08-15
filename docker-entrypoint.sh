#!/usr/bin/env sh
# Wait for the database, bring the schema up to date, optionally provision the
# first administrator, then serve the API together with the built SPA.
set -e

cd /app/backend

echo "→ Waiting for the database…"
python -m scripts.wait_for_db

echo "→ Applying database migrations…"
alembic upgrade head

echo "→ Checking administrator account…"
python -m scripts.bootstrap_admin

echo "→ Starting ${APP_NAME:-SmartCity} on port ${PORT:-8000}…"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

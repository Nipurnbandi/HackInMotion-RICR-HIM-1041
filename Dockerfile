# ─────────────────────────────────────────────────────────────
# Stage 1 — build the React frontend
# ─────────────────────────────────────────────────────────────
FROM node:22-slim AS frontend

WORKDIR /build

# Dependencies first, so this layer caches across source-only edits.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build          # → /build/dist


# ─────────────────────────────────────────────────────────────
# Stage 2 — Python runtime serving the API *and* the built SPA
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST=/app/static \
    UPLOAD_DIR=/app/uploads \
    PORT=8000

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist /app/static
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# Strip any CRLF the repo may carry from a Windows checkout, make the
# entrypoint executable, and run as a non-root user owning the upload dir.
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

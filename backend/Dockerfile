# SmartCity backend — FastAPI + PostgreSQL, built from the `backend/` context.
#
#   docker build -t smartcity-api ./backend
#
# The container migrates the database, optionally provisions the first admin,
# then serves the API. See docker-compose.yml at the repo root to run it
# together with a PostgreSQL instance.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UPLOAD_DIR=/app/uploads \
    PORT=8000

WORKDIR /app

# Dependencies first, so this layer caches across source-only edits.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Strip any CRLF a Windows checkout may carry, make the entrypoint executable,
# and run as a non-root user that owns the upload directory.
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/healthz').read()"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]

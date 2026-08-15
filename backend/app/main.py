from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, citizen, public
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_root = Path(settings.upload_dir)
upload_root.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.upload_url_prefix,
    StaticFiles(directory=upload_root),
    name="uploads",
)

app.include_router(auth.router, prefix="/api")
app.include_router(citizen.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(public.router, prefix="/api")


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness probe for the hosting platform."""
    return {"status": "ok"}


frontend_dist = Path(settings.frontend_dist) if settings.frontend_dist else None

if frontend_dist and frontend_dist.is_dir():
    # Single-container deployment: this app also serves the built React app.
    frontend_root = frontend_dist.resolve()

    @app.get("/{spa_path:path}", include_in_schema=False)
    def serve_spa(spa_path: str):
        # Unmatched /api paths are API 404s, not client-side routes.
        if spa_path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if spa_path:
            candidate = (frontend_root / spa_path).resolve()
            # Only serve files that genuinely live under the build directory.
            if frontend_root in candidate.parents and candidate.is_file():
                return FileResponse(candidate)

        # Anything else is a React Router route — return the SPA shell.
        return FileResponse(frontend_root / "index.html")

else:

    @app.get("/")
    def root():
        return {"message": "Welcome to the API"}

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/")
def root():
    return {"message": "Welcome to the API"}

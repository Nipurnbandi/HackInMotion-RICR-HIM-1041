import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import User
from app.core.roles import Role

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def citizen_user(db):
    user = User(
        email="citizen@example.com",
        hashed_password=hash_password("password123"),
        role=Role.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_citizen(db):
    user = User(
        email="other-citizen@example.com",
        hashed_password=hash_password("password123"),
        role=Role.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(autouse=True)
def seed_routing(setup_db, db, monkeypatch):
    import app.services.notification as notification_module
    import app.services.photo_verification as photo_verification_module
    from app.services.routing import seed_departments

    seed_departments(db)
    monkeypatch.setattr(notification_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(
        photo_verification_module, "SessionLocal", TestingSessionLocal
    )


@pytest.fixture(autouse=True)
def tmp_upload_dir(tmp_path, monkeypatch):
    import app.core.storage as storage_module
    from app.core.config import settings

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()

    monkeypatch.setattr(settings, "upload_dir", str(upload_root))
    monkeypatch.setattr(storage_module, "_storage", None)
    yield upload_root
    storage_module._storage = None


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        role=Role.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}

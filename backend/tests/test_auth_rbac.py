from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE
from tests.conftest import auth_header


def test_citizen_signup(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "CITIZEN"
    assert "hashed_password" not in data


def test_signup_cannot_escalate_to_admin(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "hacker@example.com",
            "password": "password123",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "CITIZEN"


def test_citizen_login(client, citizen_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "citizen@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies


def test_admin_login(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert response.status_code == 200


def test_invalid_password(client, citizen_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "citizen@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_invalid_token(client):
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_expired_token(client, citizen_user):
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {
        "sub": str(citizen_user.id),
        "role": citizen_user.role.value,
        "type": ACCESS_TOKEN_TYPE,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_citizen_can_access_citizen_endpoint(client, citizen_user):
    response = client.get(
        "/api/citizen/dashboard",
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "CITIZEN"


def test_admin_can_access_admin_endpoint(client, admin_user):
    response = client.get(
        "/api/admin/dashboard",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_citizen_cannot_access_admin_endpoint(client, citizen_user):
    response = client.get(
        "/api/admin/analytics",
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 403


def test_admin_can_access_admin_management(client, admin_user, citizen_user, db):
    from app.models import Issue

    issue = Issue(title="Test", description="desc", citizen_id=citizen_user.id)
    db.add(issue)
    db.commit()

    response = client.delete(
        f"/api/admin/issues/{issue.id}",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 204


def test_unauthenticated_cannot_access_protected(client):
    response = client.get("/api/citizen/dashboard")
    assert response.status_code == 401


def test_users_me(client, citizen_user):
    response = client.get("/api/users/me", headers=auth_header(citizen_user))
    assert response.status_code == 200
    assert response.json()["email"] == "citizen@example.com"

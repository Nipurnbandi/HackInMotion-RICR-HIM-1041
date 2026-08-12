import io
import struct

import pytest

from app.core.issue_types import IssueCategory, IssueStatus
from app.models import Issue
from tests.conftest import auth_header

VALID_DESCRIPTION = "Large pothole near the main road, dangerous for two-wheelers."


def png_bytes() -> bytes:
    """A minimal but structurally valid 1x1 PNG."""
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return header + ihdr + b"\x00" * 32


def jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 64


def issue_form(**overrides) -> dict:
    data = {
        "category": IssueCategory.POTHOLE.value,
        "description": VALID_DESCRIPTION,
        "latitude": "23.2599",
        "longitude": "77.4126",
        "address": "Example Street, Bhopal",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def make_issue(db, user, **overrides) -> Issue:
    fields = {
        "citizen_id": user.id,
        "title": "Pothole",
        "category": IssueCategory.POTHOLE,
        "description": VALID_DESCRIPTION,
        "latitude": 23.2599,
        "longitude": 77.4126,
        "status": IssueStatus.SUBMITTED,
    }
    fields.update(overrides)
    issue = Issue(**fields)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    # Mirror what the service does after flush: identifiers derived from the id.
    if issue.tracking_id is None:
        issue.tracking_id = f"SMC-2026-{issue.id:06d}"
    if issue.case_id is None:
        issue.case_id = f"CASE-{issue.id:06d}"
    db.commit()
    db.refresh(issue)
    return issue


# --- creation -----------------------------------------------------------


def test_authenticated_citizen_can_create_issue(client, citizen_user):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["category"] == "POTHOLE"
    assert body["description"] == VALID_DESCRIPTION
    assert body["latitude"] == pytest.approx(23.2599)
    assert body["longitude"] == pytest.approx(77.4126)
    assert body["address"] == "Example Street, Bhopal"
    assert body["status"] == "SUBMITTED"
    assert body["photo_url"] is None


def test_created_issue_is_persisted_with_owner(client, citizen_user, db):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201

    issue = db.get(Issue, response.json()["id"])
    assert issue is not None
    assert issue.citizen_id == citizen_user.id
    assert issue.status is IssueStatus.SUBMITTED
    assert issue.category is IssueCategory.POTHOLE


def test_tracking_id_is_generated_and_unique(client, citizen_user):
    tracking_ids = set()
    for _ in range(3):
        response = client.post(
            "/api/citizen/issues",
            data=issue_form(),
            headers=auth_header(citizen_user),
        )
        assert response.status_code == 201
        tracking_id = response.json()["tracking_id"]
        assert tracking_id.startswith("SMC-")
        assert len(tracking_id.split("-")) == 3
        tracking_ids.add(tracking_id)

    assert len(tracking_ids) == 3


def test_unauthenticated_user_cannot_create_issue(client):
    response = client.post("/api/citizen/issues", data=issue_form())
    assert response.status_code == 401


def test_admin_cannot_use_citizen_issue_endpoints(client, admin_user):
    assert (
        client.post(
            "/api/citizen/issues",
            data=issue_form(),
            headers=auth_header(admin_user),
        ).status_code
        == 403
    )
    assert (
        client.get("/api/citizen/issues", headers=auth_header(admin_user)).status_code
        == 403
    )


# --- validation ---------------------------------------------------------


def test_invalid_category_rejected(client, citizen_user):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(category="ALIEN_INVASION"),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [("91.0", "77.4"), ("-91.0", "77.4"), ("23.2", "181.0"), ("23.2", "-181.0")],
)
def test_invalid_coordinates_rejected(client, citizen_user, latitude, longitude):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(latitude=latitude, longitude=longitude),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 422


def test_missing_location_rejected(client, citizen_user):
    payload = issue_form()
    payload.pop("latitude")
    payload.pop("longitude")
    response = client.post(
        "/api/citizen/issues", data=payload, headers=auth_header(citizen_user)
    )
    assert response.status_code == 422


@pytest.mark.parametrize("description", ["", "   ", "short", "\n\t  \n"])
def test_empty_or_too_short_description_rejected(client, citizen_user, description):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(description=description),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 422


def test_description_is_trimmed(client, citizen_user):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(description=f"   {VALID_DESCRIPTION}   "),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    assert response.json()["description"] == VALID_DESCRIPTION


def test_overlong_description_rejected(client, citizen_user):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(description="x" * 2001),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 422


# --- ownership / privilege escalation ------------------------------------


def test_citizen_cannot_set_status_on_create(client, citizen_user, db):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(status="RESOLVED"),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUBMITTED"
    assert db.get(Issue, response.json()["id"]).status is IssueStatus.SUBMITTED


def test_citizen_cannot_set_owner_on_create(client, citizen_user, admin_user, db):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(citizen_id=str(admin_user.id), reporter_id=str(admin_user.id)),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    assert db.get(Issue, response.json()["id"]).citizen_id == citizen_user.id


def test_citizen_cannot_forge_tracking_id(client, citizen_user):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(tracking_id="SMC-1999-000001"),
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    assert response.json()["tracking_id"] != "SMC-1999-000001"


def test_citizen_sees_only_own_reports(client, citizen_user, other_citizen, db):
    make_issue(db, citizen_user, description="Mine: " + VALID_DESCRIPTION)
    make_issue(db, other_citizen, description="Theirs: " + VALID_DESCRIPTION)

    response = client.get("/api/citizen/issues", headers=auth_header(citizen_user))
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["description"].startswith("Mine:")


def test_citizen_cannot_read_another_citizens_issue(
    client, citizen_user, other_citizen, db
):
    theirs = make_issue(db, other_citizen)

    response = client.get(
        f"/api/citizen/issues/{theirs.id}", headers=auth_header(citizen_user)
    )
    assert response.status_code == 404


def test_citizen_can_read_own_issue(client, citizen_user, db):
    mine = make_issue(db, citizen_user)

    response = client.get(
        f"/api/citizen/issues/{mine.id}", headers=auth_header(citizen_user)
    )
    assert response.status_code == 200
    assert response.json()["id"] == mine.id


def test_unknown_issue_returns_404(client, citizen_user):
    response = client.get("/api/citizen/issues/424242", headers=auth_header(citizen_user))
    assert response.status_code == 404


def test_issue_response_hides_internal_fields(client, citizen_user, db):
    mine = make_issue(db, citizen_user)
    body = client.get(
        f"/api/citizen/issues/{mine.id}", headers=auth_header(citizen_user)
    ).json()

    assert "citizen_id" not in body
    assert "reporter" not in body
    assert "hashed_password" not in body


# --- photo evidence -----------------------------------------------------


def test_valid_photo_is_stored_and_referenced(client, citizen_user, tmp_upload_dir):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("evidence.png", io.BytesIO(png_bytes()), "image/png")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201, response.text

    photo_url = response.json()["photo_url"]
    assert photo_url.startswith("/uploads/issues/")
    assert photo_url.endswith(".png")

    stored = list((tmp_upload_dir / "issues").iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == png_bytes()


def test_jpeg_photo_accepted(client, citizen_user, tmp_upload_dir):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("evidence.jpg", io.BytesIO(jpeg_bytes()), "image/jpeg")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    assert response.json()["photo_url"].endswith(".jpg")


def test_non_image_content_rejected_despite_image_extension(
    client, citizen_user, tmp_upload_dir
):
    """An executable renamed to .png with a spoofed content type must fail."""
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("payload.png", io.BytesIO(b"MZ\x90\x00not-an-image"), "image/png")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 400
    assert "valid" in response.json()["detail"].lower()


def test_disallowed_content_type_rejected(client, citizen_user, tmp_upload_dir):
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("notes.pdf", io.BytesIO(b"%PDF-1.7"), "application/pdf")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 400


def test_oversized_photo_rejected(client, citizen_user, tmp_upload_dir):
    from app.core.config import settings

    payload = png_bytes() + b"\x00" * settings.max_upload_size_bytes
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("big.png", io.BytesIO(payload), "image/png")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 413


def test_rejected_photo_does_not_create_issue(client, citizen_user, db, tmp_upload_dir):
    client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("payload.png", io.BytesIO(b"not-an-image"), "image/png")},
        headers=auth_header(citizen_user),
    )
    assert db.query(Issue).count() == 0


# --- listing, filtering, dashboard --------------------------------------


def test_list_filters_by_status(client, citizen_user, db):
    make_issue(db, citizen_user, status=IssueStatus.SUBMITTED)
    make_issue(db, citizen_user, status=IssueStatus.RESOLVED)

    response = client.get(
        "/api/citizen/issues?status=RESOLVED", headers=auth_header(citizen_user)
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "RESOLVED"


def test_list_search_matches_description_and_address(client, citizen_user, db):
    make_issue(db, citizen_user, description="Broken light on Nehru Road for a week")
    make_issue(db, citizen_user, address="MG Road, Bhopal")

    by_description = client.get(
        "/api/citizen/issues?search=nehru", headers=auth_header(citizen_user)
    ).json()
    assert by_description["total"] == 1

    by_address = client.get(
        "/api/citizen/issues?search=mg road", headers=auth_header(citizen_user)
    ).json()
    assert by_address["total"] == 1


def test_list_is_paginated(client, citizen_user, db):
    for _ in range(5):
        make_issue(db, citizen_user)

    body = client.get(
        "/api/citizen/issues?page=2&page_size=2", headers=auth_header(citizen_user)
    ).json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 2


def test_dashboard_returns_real_stats(client, citizen_user, other_citizen, db):
    make_issue(db, citizen_user, status=IssueStatus.SUBMITTED)
    make_issue(db, citizen_user, status=IssueStatus.IN_PROGRESS)
    make_issue(db, citizen_user, status=IssueStatus.RESOLVED)
    make_issue(db, other_citizen, status=IssueStatus.RESOLVED)

    body = client.get(
        "/api/citizen/dashboard", headers=auth_header(citizen_user)
    ).json()

    assert body["issue_count"] == 3
    assert body["stats"]["total"] == 3
    assert body["stats"]["submitted"] == 1
    assert body["stats"]["in_progress"] == 1
    assert body["stats"]["resolved"] == 1
    assert body["email"] == citizen_user.email
    assert len(body["recent_issues"]) == 3


def test_stats_endpoint_scoped_to_owner(client, citizen_user, other_citizen, db):
    make_issue(db, other_citizen)

    body = client.get(
        "/api/citizen/issues/stats", headers=auth_header(citizen_user)
    ).json()
    assert body["total"] == 0

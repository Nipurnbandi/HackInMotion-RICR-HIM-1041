import io

import app.services.photo_verification as photo_verification

from tests.conftest import auth_header
from tests.test_citizen_issues import issue_form

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body-for-tests"


def fake_classifier(result):
    calls = []

    def classify_photo(*, content, media_type, prompt):
        calls.append({"media_type": media_type, "prompt": prompt})
        return result

    return classify_photo, calls


def test_report_photo_is_verified_against_category(
    client, citizen_user, monkeypatch
):
    classify, calls = fake_classifier(
        {"verdict": "MATCH", "note": "Clearly shows a damaged road surface."}
    )
    monkeypatch.setattr(photo_verification, "classify_photo", classify)

    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("road.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 201
    issue_id = response.json()["id"]

    # Background task ran after the response; the verdict is stored.
    detail = client.get(
        f"/api/citizen/issues/{issue_id}", headers=auth_header(citizen_user)
    ).json()
    assert detail["photo_verdict"] == "MATCH"
    assert detail["photo_verdict_note"] == "Clearly shows a damaged road surface."

    assert len(calls) == 1
    assert calls[0]["media_type"] == "image/png"
    assert "Pothole" in calls[0]["prompt"]


def test_mismatched_report_photo_is_flagged(client, citizen_user, monkeypatch):
    classify, _ = fake_classifier(
        {"verdict": "MISMATCH", "note": "The photo shows a cat, not a pothole."}
    )
    monkeypatch.setattr(photo_verification, "classify_photo", classify)

    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        files={"photo": ("cat.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth_header(citizen_user),
    )
    issue_id = response.json()["id"]

    detail = client.get(
        f"/api/citizen/issues/{issue_id}", headers=auth_header(citizen_user)
    ).json()
    assert detail["photo_verdict"] == "MISMATCH"


def test_report_without_photo_is_not_verified(client, citizen_user, monkeypatch):
    classify, calls = fake_classifier({"verdict": "MATCH", "note": ""})
    monkeypatch.setattr(photo_verification, "classify_photo", classify)

    response = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        headers=auth_header(citizen_user),
    )
    issue_id = response.json()["id"]

    detail = client.get(
        f"/api/citizen/issues/{issue_id}", headers=auth_header(citizen_user)
    ).json()
    assert detail["photo_verdict"] is None
    assert calls == []


def test_resolution_photo_is_verified(client, citizen_user, admin_user, monkeypatch):
    classify, calls = fake_classifier(
        {"verdict": "MATCH", "note": "The pothole appears filled and level."}
    )
    monkeypatch.setattr(photo_verification, "classify_photo", classify)

    issue_id = client.post(
        "/api/citizen/issues",
        data=issue_form(),
        headers=auth_header(citizen_user),
    ).json()["id"]

    response = client.post(
        f"/api/admin/issues/{issue_id}/resolution-photo",
        files={"photo": ("proof.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200

    detail = client.get(
        f"/api/citizen/issues/{issue_id}", headers=auth_header(citizen_user)
    ).json()
    assert detail["resolution_photo_verdict"] == "MATCH"
    assert "repaired or resolved" in calls[0]["prompt"]


def test_missing_api_key_degrades_to_unverified():
    result = photo_verification.classify_photo(
        content=PNG_BYTES, media_type="image/png", prompt="anything"
    )
    assert result["verdict"] == "UNVERIFIED"
    assert "not configured" in result["note"]

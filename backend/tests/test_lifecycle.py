import io

from tests.conftest import auth_header
from tests.test_citizen_issues import issue_form

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body-for-tests"


def report_issue(client, user, **overrides) -> dict:
    response = client.post(
        "/api/citizen/issues",
        data=issue_form(**overrides),
        headers=auth_header(user),
    )
    assert response.status_code == 201
    return response.json()


def get_detail(client, user, issue_id) -> dict:
    response = client.get(
        f"/api/citizen/issues/{issue_id}", headers=auth_header(user)
    )
    assert response.status_code == 200
    return response.json()


def test_creating_a_report_records_history(client, citizen_user):
    issue = report_issue(client, citizen_user)

    detail = get_detail(client, citizen_user, issue["id"])
    assert len(detail["history"]) == 1
    entry = detail["history"][0]
    assert entry["old_status"] is None
    assert entry["new_status"] == "SUBMITTED"
    assert entry["changed_by_role"] == "CITIZEN"
    assert "submitted" in entry["note"].lower()


def test_admin_resolution_note_and_status_are_recorded(
    client, citizen_user, admin_user
):
    issue = report_issue(client, citizen_user)

    response = client.put(
        f"/api/admin/issues/{issue['id']}",
        json={"status": "RESOLVED", "resolution_note": "Filled and re-surfaced."},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["resolution_note"] == "Filled and re-surfaced."

    detail = get_detail(client, citizen_user, issue["id"])
    assert detail["status"] == "RESOLVED"
    assert detail["resolution_note"] == "Filled and re-surfaced."

    last = detail["history"][-1]
    assert last["old_status"] == "SUBMITTED"
    assert last["new_status"] == "RESOLVED"
    assert last["note"] == "Filled and re-surfaced."
    assert last["changed_by_role"] == "ADMIN"


def test_admin_uploads_proof_of_resolution_photo(client, citizen_user, admin_user):
    issue = report_issue(client, citizen_user)

    response = client.post(
        f"/api/admin/issues/{issue['id']}/resolution-photo",
        files={"photo": ("proof.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    photo_url = response.json()["resolution_photo_url"]
    assert photo_url

    detail = get_detail(client, citizen_user, issue["id"])
    assert detail["resolution_photo_url"] == photo_url
    assert detail["history"][-1]["photo_url"] == photo_url


def test_citizen_can_confirm_a_resolved_report(client, citizen_user, admin_user):
    issue = report_issue(client, citizen_user)
    client.put(
        f"/api/admin/issues/{issue['id']}",
        json={"status": "RESOLVED"},
        headers=auth_header(admin_user),
    )

    response = client.post(
        f"/api/citizen/issues/{issue['id']}/confirm",
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESOLVED"
    assert "confirmed" in body["history"][-1]["note"].lower()
    assert body["history"][-1]["changed_by_role"] == "CITIZEN"


def test_citizen_can_reopen_a_resolved_report(client, citizen_user, admin_user):
    issue = report_issue(client, citizen_user)
    client.put(
        f"/api/admin/issues/{issue['id']}",
        json={"status": "RESOLVED"},
        headers=auth_header(admin_user),
    )

    response = client.post(
        f"/api/citizen/issues/{issue['id']}/reopen",
        headers=auth_header(citizen_user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UNDER_REVIEW"
    last = body["history"][-1]
    assert last["old_status"] == "RESOLVED"
    assert last["new_status"] == "UNDER_REVIEW"
    assert last["changed_by_role"] == "CITIZEN"


def test_only_resolved_reports_can_be_reopened_or_confirmed(client, citizen_user):
    issue = report_issue(client, citizen_user)

    for action in ("reopen", "confirm"):
        response = client.post(
            f"/api/citizen/issues/{issue['id']}/{action}",
            headers=auth_header(citizen_user),
        )
        assert response.status_code == 400


def test_reopening_a_duplicate_reopens_the_whole_case(
    client, citizen_user, other_citizen, admin_user
):
    primary = report_issue(client, citizen_user)
    duplicate = report_issue(client, other_citizen)
    assert duplicate["tracking_id"] != primary["tracking_id"]

    client.put(
        f"/api/admin/issues/{primary['id']}",
        json={"status": "RESOLVED"},
        headers=auth_header(admin_user),
    )

    # The duplicate reporter sees the case as resolved and reopens it.
    response = client.post(
        f"/api/citizen/issues/{duplicate['id']}/reopen",
        headers=auth_header(other_citizen),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UNDER_REVIEW"

    # The primary reporter sees the case reopened with the shared history.
    detail = get_detail(client, citizen_user, primary["id"])
    assert detail["status"] == "UNDER_REVIEW"
    assert detail["history"][-1]["changed_by_role"] == "CITIZEN"


def test_lifecycle_endpoints_enforce_roles(client, citizen_user, admin_user):
    issue = report_issue(client, citizen_user)

    assert (
        client.post(
            f"/api/admin/issues/{issue['id']}/resolution-photo",
            files={"photo": ("p.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers=auth_header(citizen_user),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/citizen/issues/{issue['id']}/confirm",
            headers=auth_header(admin_user),
        ).status_code
        == 403
    )

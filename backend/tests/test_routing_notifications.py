import pytest

import app.services.notification as notification_module
from app.core.issue_types import IssueCategory
from app.models import CategoryRoute, Department, Issue, Notification
from tests.conftest import auth_header
from tests.test_citizen_issues import issue_form

NEARBY = {"latitude": "23.2601", "longitude": "77.4128"}


def create(client, user, **overrides):
    response = client.post(
        "/api/citizen/issues", data=issue_form(**overrides), headers=auth_header(user)
    )
    assert response.status_code == 201, response.text
    return response.json()


def department_of(db, issue_id):
    issue = db.get(Issue, issue_id)
    return db.get(Department, issue.department_id)


@pytest.mark.parametrize(
    ("category", "expected_code"),
    [
        (IssueCategory.POTHOLE, "ROADS"),
        (IssueCategory.STREETLIGHT, "ELECTRICAL"),
        (IssueCategory.GARBAGE_OVERFLOW, "SANITATION"),
        (IssueCategory.WATER_LEAKAGE, "WATER"),
        (IssueCategory.DAMAGED_PUBLIC_PROPERTY, "PUBLIC_WORKS"),
    ],
)
def test_each_category_routes_to_its_department(
    client, citizen_user, db, category, expected_code
):
    body = create(client, citizen_user, category=category.value)
    assert department_of(db, body["id"]).code == expected_code


def test_missing_route_falls_back_to_general(client, citizen_user, db):
    db.query(CategoryRoute).filter(
        CategoryRoute.category == IssueCategory.POTHOLE
    ).delete()
    db.commit()

    body = create(client, citizen_user)
    assert department_of(db, body["id"]).code == "GENERAL"


def test_case_members_share_a_department(client, citizen_user, other_citizen, db):
    first = create(client, citizen_user)
    second = create(client, other_citizen, **NEARBY)

    assert (
        db.get(Issue, first["id"]).department_id
        == db.get(Issue, second["id"]).department_id
    )


def test_new_case_creates_one_notification(client, citizen_user, db):
    body = create(client, citizen_user)

    notifications = db.query(Notification).all()
    assert len(notifications) == 1
    assert notifications[0].issue_id == body["id"]
    assert notifications[0].department_id == db.get(Issue, body["id"]).department_id
    assert "CASE-" in notifications[0].message


def test_joined_report_does_not_notify_again(client, citizen_user, db):
    create(client, citizen_user)
    create(client, citizen_user, **NEARBY)

    assert db.query(Notification).count() == 1


def test_console_notifier_marks_notification_sent(client, citizen_user, db):
    create(client, citizen_user)

    db.expire_all()
    notification = db.query(Notification).one()
    assert notification.sent_at is not None


def test_email_failure_does_not_break_submission(client, citizen_user, db, monkeypatch):
    class BrokenNotifier:
        def send(self, *, to, subject, body):
            raise ConnectionError("mail server down")

    monkeypatch.setattr(notification_module, "get_notifier", lambda: BrokenNotifier())

    body = create(client, citizen_user)
    assert body["tracking_id"].startswith("SMC-")

    db.expire_all()
    notification = db.query(Notification).one()
    assert notification.sent_at is None


def test_department_hidden_from_citizen_response(client, citizen_user):
    body = create(client, citizen_user)
    assert "department_id" not in body
    assert "department_code" not in body


def test_admin_can_filter_queue_by_department(client, citizen_user, admin_user):
    create(client, citizen_user)
    create(client, citizen_user, category=IssueCategory.STREETLIGHT.value)

    roads = client.get(
        "/api/admin/issues?department=ROADS", headers=auth_header(admin_user)
    ).json()
    assert len(roads) == 1
    assert roads[0]["category"] == "POTHOLE"
    assert roads[0]["department_code"] == "ROADS"
    assert roads[0]["department_name"] == "Roads Department"

    everything = client.get(
        "/api/admin/issues", headers=auth_header(admin_user)
    ).json()
    assert len(everything) == 2


def test_admin_department_list_shows_open_case_counts(client, citizen_user, admin_user):
    create(client, citizen_user)
    create(client, citizen_user, **NEARBY)

    body = client.get("/api/admin/departments", headers=auth_header(admin_user)).json()
    by_code = {row["code"]: row for row in body}

    assert len(body) == 6
    assert by_code["ROADS"]["open_cases"] == 1
    assert by_code["SANITATION"]["open_cases"] == 0
    assert by_code["ROADS"]["email"] == "roads@city.gov"


def test_notifications_show_delivery_details(client, citizen_user, admin_user):
    create(client, citizen_user)

    inbox = client.get(
        "/api/admin/notifications", headers=auth_header(admin_user)
    ).json()
    item = inbox["items"][0]
    assert item["department_name"] == "Roads Department"
    assert item["department_email"] == "roads@city.gov"
    assert item["sent_at"] is not None


def test_failed_email_shows_as_pending(client, citizen_user, admin_user, monkeypatch):
    class BrokenNotifier:
        def send(self, *, to, subject, body):
            raise ConnectionError("mail server down")

    monkeypatch.setattr(notification_module, "get_notifier", lambda: BrokenNotifier())
    create(client, citizen_user)

    inbox = client.get(
        "/api/admin/notifications", headers=auth_header(admin_user)
    ).json()
    assert inbox["items"][0]["sent_at"] is None


def test_admin_status_update_reaches_the_citizen(client, citizen_user, admin_user):
    body = create(client, citizen_user)

    response = client.put(
        f"/api/admin/issues/{body['id']}",
        json={"status": "IN_PROGRESS"},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"

    detail = client.get(
        f"/api/citizen/issues/{body['id']}", headers=auth_header(citizen_user)
    ).json()
    assert detail["status"] == "IN_PROGRESS"


def test_admin_notification_inbox_and_mark_read(client, citizen_user, admin_user):
    create(client, citizen_user)

    inbox = client.get(
        "/api/admin/notifications", headers=auth_header(admin_user)
    ).json()
    assert inbox["unread"] == 1
    assert len(inbox["items"]) == 1
    assert inbox["items"][0]["is_read"] is False

    notification_id = inbox["items"][0]["id"]
    marked = client.post(
        f"/api/admin/notifications/{notification_id}/read",
        headers=auth_header(admin_user),
    ).json()
    assert marked["is_read"] is True

    inbox = client.get(
        "/api/admin/notifications", headers=auth_header(admin_user)
    ).json()
    assert inbox["unread"] == 0


def test_citizen_cannot_access_admin_notification_endpoints(client, citizen_user):
    assert (
        client.get(
            "/api/admin/notifications", headers=auth_header(citizen_user)
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/admin/departments", headers=auth_header(citizen_user)
        ).status_code
        == 403
    )

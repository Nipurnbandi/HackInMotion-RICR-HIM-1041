"""Silent duplicate detection: repeat reports join a shared case.

The four-condition check (category, ~50 m box, 7-day window, case still open),
the case labelling, status read-through, and the invisibility guarantees.
"""

from datetime import datetime, timedelta

from app.core.issue_types import IssueCategory, IssueStatus
from app.models import Issue
from tests.conftest import auth_header
from tests.test_citizen_issues import issue_form, make_issue

# The default form location (23.2599, 77.4126) is the reference point.
# 0.0002° of latitude ≈ 22 m (inside the 50 m box); 0.001° ≈ 111 m (outside).
NEARBY = {"latitude": "23.2601", "longitude": "77.4128"}
FAR_AWAY = {"latitude": "23.2609", "longitude": "77.4126"}


def create(client, user, **overrides):
    response = client.post(
        "/api/citizen/issues", data=issue_form(**overrides), headers=auth_header(user)
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- grouping ------------------------------------------------------------


def test_nearby_same_category_joins_the_case(client, citizen_user, db):
    first = create(client, citizen_user)
    second = create(client, citizen_user, **NEARBY)

    a, b = db.get(Issue, first["id"]), db.get(Issue, second["id"])
    assert a.case_id is not None
    assert a.case_id == b.case_id
    assert a.is_primary is True
    assert b.is_primary is False
    # Each still owns its identity.
    assert first["tracking_id"] != second["tracking_id"]


def test_third_report_attaches_to_the_case_not_a_chain(client, citizen_user, db):
    first = create(client, citizen_user)
    create(client, citizen_user, **NEARBY)
    third = create(client, citizen_user, latitude="23.2598", longitude="77.4125")

    a, c = db.get(Issue, first["id"]), db.get(Issue, third["id"])
    assert c.case_id == a.case_id
    # Exactly one primary per case, however many join.
    primaries = db.query(Issue).filter(
        Issue.case_id == a.case_id, Issue.is_primary.is_(True)
    )
    assert primaries.count() == 1


def test_different_category_opens_a_new_case(client, citizen_user, db):
    first = create(client, citizen_user)
    second = create(client, citizen_user, category=IssueCategory.STREETLIGHT.value)

    assert db.get(Issue, first["id"]).case_id != db.get(Issue, second["id"]).case_id
    assert db.get(Issue, second["id"]).is_primary is True


def test_report_outside_the_box_opens_a_new_case(client, citizen_user, db):
    first = create(client, citizen_user)
    second = create(client, citizen_user, **FAR_AWAY)

    assert db.get(Issue, first["id"]).case_id != db.get(Issue, second["id"]).case_id


def test_report_older_than_the_category_window_is_not_joined(client, citizen_user, db):
    # Pothole window is 60 days: a 90-day-old report is a different event.
    old = make_issue(
        db, citizen_user, created_at=datetime.utcnow() - timedelta(days=90)
    )
    fresh = create(client, citizen_user)

    assert db.get(Issue, fresh["id"]).case_id != old.case_id
    assert db.get(Issue, fresh["id"]).is_primary is True


def test_window_is_per_category(client, citizen_user, db):
    """A 10-day-old pothole still absorbs (60-day window); a 10-day-old
    garbage report does not (3-day window — the bin was emptied since)."""
    old_pothole = make_issue(
        db, citizen_user, created_at=datetime.utcnow() - timedelta(days=10)
    )
    joined = create(client, citizen_user)
    assert db.get(Issue, joined["id"]).case_id == old_pothole.case_id

    old_garbage = make_issue(
        db,
        citizen_user,
        category=IssueCategory.GARBAGE_OVERFLOW,
        latitude=23.5,
        longitude=77.5,
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    fresh_garbage = create(
        client,
        citizen_user,
        category=IssueCategory.GARBAGE_OVERFLOW.value,
        latitude="23.5",
        longitude="77.5",
    )
    assert db.get(Issue, fresh_garbage["id"]).case_id != old_garbage.case_id


def test_radius_is_per_category(client, citizen_user, db):
    """~55 m apart: outside a pothole's 25 m radius, inside a water leak's 80 m."""
    offset = {"latitude": "23.26040"}  # 0.0005 deg ≈ 55 m north of the default

    pothole = create(client, citizen_user)
    far_pothole = create(client, citizen_user, **offset)
    assert (
        db.get(Issue, pothole["id"]).case_id
        != db.get(Issue, far_pothole["id"]).case_id
    )

    leak = create(client, citizen_user, category=IssueCategory.WATER_LEAKAGE.value)
    far_leak = create(
        client, citizen_user, category=IssueCategory.WATER_LEAKAGE.value, **offset
    )
    assert db.get(Issue, leak["id"]).case_id == db.get(Issue, far_leak["id"]).case_id


def test_closed_case_is_never_joined(client, citizen_user, db):
    """A problem that reappears after being fixed is a new problem."""
    resolved = make_issue(db, citizen_user, status=IssueStatus.RESOLVED)
    fresh = create(client, citizen_user)

    assert db.get(Issue, fresh["id"]).case_id != resolved.case_id
    assert db.get(Issue, fresh["id"]).is_primary is True


def test_grouping_ignores_who_reported(client, citizen_user, other_citizen, db):
    first = create(client, citizen_user)
    second = create(client, other_citizen, **NEARBY)

    assert db.get(Issue, first["id"]).case_id == db.get(Issue, second["id"]).case_id


# --- invisibility --------------------------------------------------------


def test_case_fields_never_reach_the_citizen(client, citizen_user):
    create(client, citizen_user)
    joined = create(client, citizen_user, **NEARBY)

    for body in (joined, *[
        client.get(f"/api/citizen/issues/{joined['id']}", headers=auth_header(citizen_user)).json()
    ]):
        assert "case_id" not in body
        assert "is_primary" not in body


def test_joined_report_still_appears_in_my_reports(client, citizen_user):
    create(client, citizen_user)
    create(client, citizen_user, **NEARBY)

    listing = client.get("/api/citizen/issues", headers=auth_header(citizen_user)).json()
    assert listing["total"] == 2  # the citizen's own view is never de-duplicated


def test_create_response_always_says_submitted(client, citizen_user, db):
    first = create(client, citizen_user)
    # The case moves on before the second person reports.
    primary = db.get(Issue, first["id"])
    primary.status = IssueStatus.UNDER_REVIEW
    db.commit()

    joined = create(client, citizen_user, **NEARBY)
    assert joined["status"] == "SUBMITTED"  # a fresh submit must look fresh


# --- status read-through -------------------------------------------------


def test_joined_report_reads_status_from_the_primary(client, citizen_user, db):
    first = create(client, citizen_user)
    joined = create(client, citizen_user, **NEARBY)

    db.get(Issue, first["id"]).status = IssueStatus.IN_PROGRESS
    db.commit()

    detail = client.get(
        f"/api/citizen/issues/{joined['id']}", headers=auth_header(citizen_user)
    ).json()
    assert detail["status"] == "IN_PROGRESS"

    listing = client.get("/api/citizen/issues", headers=auth_header(citizen_user)).json()
    statuses = {item["id"]: item["status"] for item in listing["items"]}
    assert statuses[joined["id"]] == "IN_PROGRESS"
    assert statuses[first["id"]] == "IN_PROGRESS"


def test_read_through_does_not_change_stored_status(client, citizen_user, db):
    first = create(client, citizen_user)
    joined = create(client, citizen_user, **NEARBY)
    db.get(Issue, first["id"]).status = IssueStatus.RESOLVED
    db.commit()

    client.get(f"/api/citizen/issues/{joined['id']}", headers=auth_header(citizen_user))
    client.get("/api/citizen/issues", headers=auth_header(citizen_user))

    db.expire_all()
    assert db.get(Issue, joined["id"]).status is IssueStatus.SUBMITTED


def test_status_filter_matches_the_effective_status(client, citizen_user, db):
    first = create(client, citizen_user)
    joined = create(client, citizen_user, **NEARBY)
    db.get(Issue, first["id"]).status = IssueStatus.IN_PROGRESS
    db.commit()

    body = client.get(
        "/api/citizen/issues?status=IN_PROGRESS", headers=auth_header(citizen_user)
    ).json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {first["id"], joined["id"]}

    # Nothing is SUBMITTED any more from the citizen's point of view.
    submitted = client.get(
        "/api/citizen/issues?status=SUBMITTED", headers=auth_header(citizen_user)
    ).json()
    assert submitted["total"] == 0


def test_stats_bucket_by_effective_status(client, citizen_user, db):
    first = create(client, citizen_user)
    create(client, citizen_user, **NEARBY)
    db.get(Issue, first["id"]).status = IssueStatus.RESOLVED
    db.commit()

    stats = client.get(
        "/api/citizen/issues/stats", headers=auth_header(citizen_user)
    ).json()
    assert stats["total"] == 2
    assert stats["resolved"] == 2
    assert stats["submitted"] == 0


# --- the city's view -----------------------------------------------------


def test_admin_list_shows_one_row_per_case(client, citizen_user, admin_user):
    create(client, citizen_user)
    create(client, citizen_user, **NEARBY)
    create(client, citizen_user, category=IssueCategory.STREETLIGHT.value)

    body = client.get("/api/admin/issues", headers=auth_header(admin_user)).json()
    assert len(body) == 2  # two real problems, three reports


def test_admin_list_exposes_citizen_count_and_priority(
    client, citizen_user, other_citizen, admin_user
):
    create(client, citizen_user)                     # pothole, 2 citizens
    create(client, other_citizen, **NEARBY)
    create(client, citizen_user, category=IssueCategory.GARBAGE_OVERFLOW.value)

    body = client.get("/api/admin/issues", headers=auth_header(admin_user)).json()
    by_category = {row["category"]: row for row in body}

    pothole = by_category["POTHOLE"]
    garbage = by_category["GARBAGE_OVERFLOW"]
    assert pothole["citizen_count"] == 2
    assert garbage["citizen_count"] == 1
    # severity 4 x 2 citizens beats severity 2 x 1 citizen; list is ordered.
    assert pothole["priority_score"] > garbage["priority_score"]
    assert body[0]["category"] == "POTHOLE"


def test_priority_counts_distinct_citizens_not_reports(client, citizen_user, admin_user):
    """One person spamming five reports is still one voice."""
    create(client, citizen_user)
    create(client, citizen_user, **NEARBY)
    create(client, citizen_user, latitude="23.2598")

    body = client.get("/api/admin/issues", headers=auth_header(admin_user)).json()
    assert len(body) == 1
    assert body[0]["citizen_count"] == 1


def test_age_lifts_an_ignored_case(client, citizen_user, admin_user, db):
    """A lone month-old streetlight outranks a fresh one with two reporters.

    severity 3 x 1 citizen x (1 + 30/7) = 15.9  vs  3 x 1 x 1 = 3.
    """
    make_issue(
        db,
        citizen_user,
        category=IssueCategory.STREETLIGHT,
        latitude=23.5,
        longitude=77.5,
        created_at=datetime.utcnow() - timedelta(days=30),
    )
    create(client, citizen_user, category=IssueCategory.STREETLIGHT.value)

    body = client.get("/api/admin/issues", headers=auth_header(admin_user)).json()
    assert body[0]["days_open"] >= 29
    assert body[0]["priority_score"] > body[1]["priority_score"]


def test_admin_resolving_the_case_updates_every_member(client, citizen_user, admin_user, db):
    first = create(client, citizen_user)
    joined = create(client, citizen_user, **NEARBY)

    response = client.put(
        f"/api/admin/issues/{first['id']}",
        json={"status": "RESOLVED"},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200

    detail = client.get(
        f"/api/citizen/issues/{joined['id']}", headers=auth_header(citizen_user)
    ).json()
    assert detail["status"] == "RESOLVED"

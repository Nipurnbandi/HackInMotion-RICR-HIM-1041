from datetime import datetime, timedelta, timezone

from app.core.issue_types import IssueCategory, IssueStatus
from app.models import Department, Issue

from tests.conftest import auth_header


def make_issue(
    db,
    *,
    citizen,
    category,
    case_id,
    status=IssueStatus.SUBMITTED,
    is_primary=True,
    latitude=None,
    longitude=None,
    address=None,
    department_code=None,
    created_at=None,
    updated_at=None,
    tracking_id=None,
):
    department_id = None
    if department_code:
        department_id = (
            db.query(Department).filter(Department.code == department_code).one().id
        )
    now = datetime.now(timezone.utc)
    issue = Issue(
        citizen_id=citizen.id,
        title=category.value.title(),
        category=category,
        description="Seeded issue for analytics tests.",
        status=status,
        case_id=case_id,
        is_primary=is_primary,
        latitude=latitude,
        longitude=longitude,
        address=address,
        department_id=department_id,
        tracking_id=tracking_id,
        created_at=created_at or now,
        updated_at=updated_at or created_at or now,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def seed_city(db, citizen_user, other_citizen):
    now = datetime.now(timezone.utc)

    # Case A: resolved pothole, two reports, took 3 days to resolve.
    make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.POTHOLE,
        case_id="CASE-A",
        status=IssueStatus.RESOLVED,
        latitude=23.2599,
        longitude=77.4126,
        address="Main Road, Bhopal",
        department_code="ROADS",
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=1),
        tracking_id="SMC-A1",
    )
    make_issue(
        db,
        citizen=other_citizen,
        category=IssueCategory.POTHOLE,
        case_id="CASE-A",
        status=IssueStatus.RESOLVED,
        is_primary=False,
        latitude=23.2599,
        longitude=77.4126,
        department_code="ROADS",
        created_at=now - timedelta(days=3),
        tracking_id="SMC-A2",
    )

    # Case B: open garbage report in the same ~110m map cell as case A.
    make_issue(
        db,
        citizen=other_citizen,
        category=IssueCategory.GARBAGE_OVERFLOW,
        case_id="CASE-B",
        status=IssueStatus.SUBMITTED,
        latitude=23.2601,
        longitude=77.4128,
        address="Market Corner, Bhopal",
        department_code="SANITATION",
        created_at=now - timedelta(days=1),
        tracking_id="SMC-B1",
    )

    # A report without coordinates never reaches the map or hotspots.
    make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.STREETLIGHT,
        case_id="CASE-C",
        status=IssueStatus.UNDER_REVIEW,
        department_code="ELECTRICAL",
        created_at=now - timedelta(days=2),
        tracking_id="SMC-C1",
    )


def test_analytics_aggregates_real_database_state(
    client, db, admin_user, citizen_user, other_citizen
):
    seed_city(db, citizen_user, other_citizen)

    response = client.get("/api/admin/analytics", headers=auth_header(admin_user))
    assert response.status_code == 200
    data = response.json()

    assert data["total_issues"] == 3
    assert data["total_reports"] == 4
    assert data["open_issues"] == 2
    assert data["closed_issues"] == 1
    assert data["total_citizens"] == 2
    assert data["avg_resolution_days"] == 3.0

    by_category = {row["category"]: row for row in data["by_category"]}
    assert by_category["POTHOLE"]["count"] == 1
    assert by_category["POTHOLE"]["label"] == "Pothole"
    assert by_category["GARBAGE_OVERFLOW"]["count"] == 1
    assert by_category["WATER_LEAKAGE"]["count"] == 0

    by_status = {row["status"]: row["count"] for row in data["by_status"]}
    assert by_status["RESOLVED"] == 1
    assert by_status["SUBMITTED"] == 1
    assert by_status["UNDER_REVIEW"] == 1
    assert by_status["IN_PROGRESS"] == 0

    departments = {row["code"]: row for row in data["departments"]}
    assert departments["ROADS"]["total_cases"] == 1
    assert departments["ROADS"]["resolved_cases"] == 1
    assert departments["ROADS"]["open_cases"] == 0
    assert departments["ROADS"]["avg_resolution_days"] == 3.0
    assert departments["SANITATION"]["open_cases"] == 1
    assert departments["SANITATION"]["avg_resolution_days"] is None
    assert departments["WATER"]["total_cases"] == 0


def test_analytics_detects_hotspots(client, db, admin_user, citizen_user, other_citizen):
    seed_city(db, citizen_user, other_citizen)

    response = client.get("/api/admin/analytics", headers=auth_header(admin_user))
    assert response.status_code == 200
    hotspots = response.json()["hotspots"]

    assert len(hotspots) == 1
    hotspot = hotspots[0]
    assert hotspot["case_count"] == 2
    assert hotspot["report_count"] == 3
    # The most recent report in the cell carries the display address.
    assert hotspot["address"] == "Market Corner, Bhopal"
    assert hotspot["latitude"] == 23.26
    assert hotspot["longitude"] == 77.413


def test_map_endpoints_return_colored_marker_data(
    client, db, admin_user, citizen_user, other_citizen
):
    seed_city(db, citizen_user, other_citizen)

    admin_response = client.get("/api/admin/map", headers=auth_header(admin_user))
    assert admin_response.status_code == 200
    markers = admin_response.json()

    # Only primary issues with coordinates appear, newest first.
    assert [marker["category"] for marker in markers] == [
        "GARBAGE_OVERFLOW",
        "POTHOLE",
    ]
    pothole = markers[1]
    assert pothole["status"] == "RESOLVED"
    assert pothole["report_count"] == 2
    assert pothole["citizen_count"] == 2
    assert pothole["department_name"] == "Roads Department"
    assert pothole["latitude"] == 23.2599

    citizen_response = client.get("/api/citizen/map", headers=auth_header(citizen_user))
    assert citizen_response.status_code == 200
    assert len(citizen_response.json()) == 2


def test_map_and_analytics_respect_role_guards(client, admin_user, citizen_user):
    assert (
        client.get("/api/admin/map", headers=auth_header(citizen_user)).status_code
        == 403
    )
    assert (
        client.get("/api/citizen/map", headers=auth_header(admin_user)).status_code
        == 403
    )

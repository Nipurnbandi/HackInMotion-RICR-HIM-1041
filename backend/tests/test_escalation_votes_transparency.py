from datetime import datetime, timedelta, timezone

from app.core.issue_types import IssueCategory, IssueStatus
from app.models import Notification

from tests.conftest import auth_header
from tests.test_admin_analytics import make_issue


def test_sla_breach_escalates_case_once(client, db, admin_user, citizen_user):
    now = datetime.now(timezone.utc)
    # Garbage overflow has a 2-day SLA; this case is 5 days old and still open.
    overdue = make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.GARBAGE_OVERFLOW,
        case_id="CASE-OVERDUE",
        status=IssueStatus.SUBMITTED,
        latitude=23.26,
        longitude=77.41,
        department_code="SANITATION",
        created_at=now - timedelta(days=5),
        tracking_id="SMC-OVER-1",
    )
    # A fresh pothole (7-day SLA) must NOT escalate.
    make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.POTHOLE,
        case_id="CASE-FRESH",
        status=IssueStatus.SUBMITTED,
        latitude=23.27,
        longitude=77.42,
        department_code="ROADS",
        created_at=now - timedelta(days=1),
        tracking_id="SMC-FRESH-1",
    )

    response = client.get("/api/admin/issues", headers=auth_header(admin_user))
    assert response.status_code == 200
    cases = {case["tracking_id"]: case for case in response.json()}

    assert cases["SMC-OVER-1"]["escalated"] is True
    assert cases["SMC-OVER-1"]["sla_days"] == 2
    assert cases["SMC-FRESH-1"]["escalated"] is False

    # The higher authority (General Administration) got notified.
    notes = db.query(Notification).filter(Notification.issue_id == overdue.id).all()
    assert any("SLA BREACH" in note.message for note in notes)

    # Escalation boosts priority: 2 (severity) × 1 citizen × (1 + 5/7) × 1.5
    assert cases["SMC-OVER-1"]["priority_score"] == round(
        2 * 1 * (1 + 5 / 7) * 1.5, 1
    )

    # Idempotent: a second sweep does not duplicate notifications or history.
    client.get("/api/admin/issues", headers=auth_header(admin_user))
    assert (
        db.query(Notification).filter(Notification.issue_id == overdue.id).count()
        == len(notes)
    )

    # The escalation is visible in the case history for the reporter.
    detail = client.get(
        f"/api/citizen/issues/{overdue.id}", headers=auth_header(citizen_user)
    ).json()
    assert any("Escalated to higher authority" in e["note"] for e in detail["history"])


def test_citizen_can_upvote_and_unvote_a_case(
    client, db, citizen_user, other_citizen, admin_user
):
    issue = make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.POTHOLE,
        case_id="CASE-VOTE",
        latitude=23.26,
        longitude=77.41,
        department_code="ROADS",
        tracking_id="SMC-VOTE-1",
    )

    # Another citizen upvotes it.
    response = client.post(
        f"/api/citizen/issues/{issue.id}/vote", headers=auth_header(other_citizen)
    )
    assert response.status_code == 200
    assert response.json() == {
        "issue_id": issue.id,
        "vote_count": 1,
        "has_voted": True,
    }

    # The vote shows on their map and feeds the admin priority.
    city_map = client.get("/api/citizen/map", headers=auth_header(other_citizen)).json()
    marker = next(m for m in city_map if m["id"] == issue.id)
    assert marker["vote_count"] == 1
    assert marker["has_voted"] is True

    cases = client.get("/api/admin/issues", headers=auth_header(admin_user)).json()
    case = next(c for c in cases if c["id"] == issue.id)
    assert case["vote_count"] == 1
    # severity 4 × (1 reporter + 1 vote) × age factor 1.0
    assert case["priority_score"] == 8.0

    # Voting again withdraws the vote.
    response = client.post(
        f"/api/citizen/issues/{issue.id}/vote", headers=auth_header(other_citizen)
    )
    assert response.json()["vote_count"] == 0
    assert response.json()["has_voted"] is False


def test_reporters_cannot_upvote_their_own_case(client, db, citizen_user):
    issue = make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.POTHOLE,
        case_id="CASE-OWN",
        latitude=23.26,
        longitude=77.41,
        department_code="ROADS",
        tracking_id="SMC-OWN-1",
    )

    response = client.post(
        f"/api/citizen/issues/{issue.id}/vote", headers=auth_header(citizen_user)
    )
    assert response.status_code == 400
    assert "already counts" in response.json()["detail"]


def test_transparency_report_is_public_and_scored(
    client, db, citizen_user, other_citizen
):
    now = datetime.now(timezone.utc)
    # Roads: one case resolved in 2 days (inside its 7-day SLA).
    make_issue(
        db,
        citizen=citizen_user,
        category=IssueCategory.POTHOLE,
        case_id="CASE-T1",
        status=IssueStatus.RESOLVED,
        latitude=23.26,
        longitude=77.41,
        department_code="ROADS",
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=1),
        tracking_id="SMC-T1",
    )
    # Sanitation: one open case.
    make_issue(
        db,
        citizen=other_citizen,
        category=IssueCategory.GARBAGE_OVERFLOW,
        case_id="CASE-T2",
        status=IssueStatus.SUBMITTED,
        latitude=23.27,
        longitude=77.42,
        department_code="SANITATION",
        created_at=now - timedelta(days=1),
        tracking_id="SMC-T2",
    )

    # No auth header at all — the page is public.
    response = client.get("/api/public/transparency")
    assert response.status_code == 200
    report = response.json()

    departments = {row["code"]: row for row in report["departments"]}

    roads = departments["ROADS"]
    assert roads["total_cases"] == 1
    assert roads["resolved_cases"] == 1
    assert roads["resolution_rate"] == 100
    assert roads["on_time_rate"] == 100
    assert roads["avg_resolution_days"] == 2.0
    # 0.5×1 + 0.3×1 + 0.2×(1 - 2/14) = 0.9714… → 97
    assert roads["score"] == 97
    assert roads["grade"] == "A+"

    sanitation = departments["SANITATION"]
    assert sanitation["resolution_rate"] == 0
    assert sanitation["score"] == 0
    assert sanitation["grade"] == "D"

    # Departments without cases show no score rather than a fake one.
    assert departments["WATER"]["score"] is None
    assert departments["WATER"]["grade"] is None

    assert report["city"]["total_cases"] == 2
    assert "resolution rate" in report["methodology"]

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.issue_types import CLOSED_STATUSES, SLA_DAYS, IssueStatus
from app.models import Department, Issue

# Score weights: did problems get fixed, were they fixed inside the SLA,
# and how fast on average. Documented publicly on the transparency page.
WEIGHT_RESOLUTION_RATE = 0.5
WEIGHT_ON_TIME_RATE = 0.3
WEIGHT_SPEED = 0.2
SPEED_NORM_DAYS = 14.0


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _resolution_days(issue: Issue) -> float:
    delta = _as_utc(issue.updated_at) - _as_utc(issue.created_at)
    return max(delta.total_seconds() / 86400, 0.0)


def grade_for(score: int) -> str:
    if score >= 85:
        return "A+"
    if score >= 70:
        return "A"
    if score >= 55:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _department_card(name: str, code: str, issues: list[Issue]) -> dict:
    total = len(issues)
    resolved = [issue for issue in issues if issue.status == IssueStatus.RESOLVED]
    open_cases = sum(1 for issue in issues if issue.status not in CLOSED_STATUSES)
    escalated = sum(1 for issue in issues if issue.escalated_at is not None)

    card = {
        "code": code,
        "name": name,
        "total_cases": total,
        "open_cases": open_cases,
        "resolved_cases": len(resolved),
        "escalated_cases": escalated,
        "resolution_rate": None,
        "on_time_rate": None,
        "avg_resolution_days": None,
        "score": None,
        "grade": None,
    }
    if total == 0:
        return card

    resolution_rate = len(resolved) / total
    card["resolution_rate"] = round(resolution_rate * 100)

    on_time_rate = 0.0
    speed_factor = 0.0
    if resolved:
        on_time = sum(
            1
            for issue in resolved
            if _resolution_days(issue) <= SLA_DAYS[issue.category]
        )
        on_time_rate = on_time / len(resolved)
        avg_days = sum(_resolution_days(issue) for issue in resolved) / len(resolved)
        card["on_time_rate"] = round(on_time_rate * 100)
        card["avg_resolution_days"] = round(avg_days, 1)
        speed_factor = max(0.0, 1.0 - avg_days / SPEED_NORM_DAYS)

    score = round(
        100
        * (
            WEIGHT_RESOLUTION_RATE * resolution_rate
            + WEIGHT_ON_TIME_RATE * on_time_rate
            + WEIGHT_SPEED * speed_factor
        )
    )
    card["score"] = score
    card["grade"] = grade_for(score)
    return card


def build_transparency_report(db: Session) -> dict:
    primaries = (
        db.query(Issue)
        .options(joinedload(Issue.department))
        .filter(Issue.is_primary.is_(True))
        .all()
    )

    by_department: dict[int | None, list[Issue]] = {}
    for issue in primaries:
        by_department.setdefault(issue.department_id, []).append(issue)

    departments = [
        _department_card(
            department.name,
            department.code,
            by_department.get(department.id, []),
        )
        for department in db.query(Department).order_by(Department.name).all()
    ]
    departments.sort(key=lambda card: (card["score"] is None, -(card["score"] or 0)))

    city = _department_card("City-wide", "CITY", primaries)

    return {
        "generated_at": datetime.now(timezone.utc),
        "city": city,
        "departments": departments,
        "methodology": (
            f"Score = {int(WEIGHT_RESOLUTION_RATE * 100)}% resolution rate + "
            f"{int(WEIGHT_ON_TIME_RATE * 100)}% resolved-within-SLA rate + "
            f"{int(WEIGHT_SPEED * 100)}% speed (average resolution time measured "
            f"against a {int(SPEED_NORM_DAYS)}-day baseline), computed live from "
            f"the city's report database."
        ),
    }

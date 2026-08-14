from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Issue


def case_report_counts(db: Session) -> dict[str | None, tuple[int, int]]:
    """Reports and distinct citizens per case, member issues included."""
    rows = db.execute(
        select(
            Issue.case_id,
            func.count(Issue.id),
            func.count(func.distinct(Issue.citizen_id)),
        ).group_by(Issue.case_id)
    ).all()
    return {case_id: (reports, citizens) for case_id, reports, citizens in rows}


def list_map_issues(db: Session) -> list[dict]:
    issues = (
        db.query(Issue)
        .options(joinedload(Issue.department))
        .filter(
            Issue.is_primary.is_(True),
            Issue.latitude.isnot(None),
            Issue.longitude.isnot(None),
        )
        .order_by(Issue.created_at.desc())
        .all()
    )
    counts = case_report_counts(db)

    return [
        {
            "id": issue.id,
            "tracking_id": issue.tracking_id,
            "category": issue.category,
            "status": issue.status,
            "latitude": issue.latitude,
            "longitude": issue.longitude,
            "address": issue.address,
            "created_at": issue.created_at,
            "report_count": counts.get(issue.case_id, (1, 1))[0],
            "citizen_count": counts.get(issue.case_id, (1, 1))[1],
            "department_name": issue.department.name if issue.department else None,
        }
        for issue in issues
    ]

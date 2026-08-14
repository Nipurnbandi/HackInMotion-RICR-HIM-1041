from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.issue_types import (
    CATEGORY_LABELS,
    CLOSED_STATUSES,
    SEVERITY_WEIGHTS,
    IssueStatus,
)
from app.core.roles import Role
from app.core.storage import Storage, get_storage
from app.models import Department, Issue, User
from app.schemas.admin import IssueUpdate
from app.services.city_map import case_report_counts
from app.services.lifecycle import record_status_change

HOTSPOT_CELL_PRECISION = 3  # ~110m grid cells
HOTSPOT_MIN_REPORTS = 2
HOTSPOT_LIMIT = 8


def get_admin_dashboard(db: Session, user: User) -> dict:
    total_issues = db.query(Issue).filter(Issue.is_primary.is_(True)).count()
    total_citizens = db.query(User).filter(User.role == Role.CITIZEN).count()
    return {
        "message": "Welcome to the Admin Dashboard.",
        "role": user.role.value,
        "total_issues": total_issues,
        "total_citizens": total_citizens,
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _resolution_days(issue: Issue) -> float:
    delta = _as_utc(issue.updated_at) - _as_utc(issue.created_at)
    return max(delta.total_seconds() / 86400, 0.0)


def _average_resolution_days(issues: list[Issue]) -> float | None:
    resolved = [issue for issue in issues if issue.status == IssueStatus.RESOLVED]
    if not resolved:
        return None
    return round(sum(_resolution_days(issue) for issue in resolved) / len(resolved), 1)


def _department_stats(code: str | None, name: str, issues: list[Issue]) -> dict:
    return {
        "code": code,
        "name": name,
        "total_cases": len(issues),
        "open_cases": sum(
            1 for issue in issues if issue.status not in CLOSED_STATUSES
        ),
        "resolved_cases": sum(
            1 for issue in issues if issue.status == IssueStatus.RESOLVED
        ),
        "avg_resolution_days": _average_resolution_days(issues),
    }


def _find_hotspots(
    primaries: list[Issue], case_counts: dict[str | None, tuple[int, int]]
) -> list[dict]:
    cells: dict[tuple[float, float], list[Issue]] = defaultdict(list)
    for issue in primaries:
        if issue.latitude is None or issue.longitude is None:
            continue
        cells[
            (
                round(issue.latitude, HOTSPOT_CELL_PRECISION),
                round(issue.longitude, HOTSPOT_CELL_PRECISION),
            )
        ].append(issue)

    hotspots = []
    for (latitude, longitude), issues in cells.items():
        report_count = sum(
            case_counts.get(issue.case_id, (1, 1))[0] for issue in issues
        )
        if report_count < HOTSPOT_MIN_REPORTS:
            continue
        top_category = Counter(issue.category for issue in issues).most_common(1)[0][0]
        newest_first = sorted(
            issues, key=lambda issue: _as_utc(issue.created_at), reverse=True
        )
        hotspots.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "case_count": len(issues),
                "report_count": report_count,
                "address": next(
                    (issue.address for issue in newest_first if issue.address), None
                ),
                "top_category": top_category,
                "top_category_label": CATEGORY_LABELS[top_category],
            }
        )

    hotspots.sort(
        key=lambda spot: (spot["report_count"], spot["case_count"]), reverse=True
    )
    return hotspots[:HOTSPOT_LIMIT]


def get_admin_analytics(db: Session) -> dict:
    primaries = (
        db.query(Issue)
        .options(joinedload(Issue.department))
        .filter(Issue.is_primary.is_(True))
        .all()
    )
    case_counts = case_report_counts(db)
    total_reports = db.query(Issue).count()
    total_citizens = db.query(User).filter(User.role == Role.CITIZEN).count()

    open_issues = sum(
        1 for issue in primaries if issue.status not in CLOSED_STATUSES
    )

    category_counts = Counter(issue.category for issue in primaries)
    by_category = sorted(
        (
            {"category": category, "label": label, "count": category_counts[category]}
            for category, label in CATEGORY_LABELS.items()
        ),
        key=lambda row: row["count"],
        reverse=True,
    )

    status_counts = Counter(issue.status for issue in primaries)
    by_status = [
        {"status": status_value, "count": status_counts[status_value]}
        for status_value in IssueStatus
    ]

    issues_by_department: dict[int, list[Issue]] = defaultdict(list)
    unassigned: list[Issue] = []
    for issue in primaries:
        if issue.department_id is None:
            unassigned.append(issue)
        else:
            issues_by_department[issue.department_id].append(issue)

    departments = [
        _department_stats(
            department.code,
            department.name,
            issues_by_department.get(department.id, []),
        )
        for department in db.query(Department).order_by(Department.name).all()
    ]
    if unassigned:
        departments.append(_department_stats(None, "Unassigned", unassigned))

    return {
        "total_issues": len(primaries),
        "open_issues": open_issues,
        "closed_issues": len(primaries) - open_issues,
        "total_citizens": total_citizens,
        "total_reports": total_reports,
        "avg_resolution_days": _average_resolution_days(primaries),
        "by_category": by_category,
        "by_status": by_status,
        "departments": departments,
        "hotspots": _find_hotspots(primaries, case_counts),
    }


def list_admin_cases(db: Session, *, department_code: str | None = None) -> list[dict]:
    member = aliased(Issue)
    citizens = func.count(func.distinct(member.citizen_id))

    query = (
        select(Issue, citizens)
        .join(member, member.case_id == Issue.case_id)
        .where(Issue.is_primary.is_(True))
        .group_by(Issue.id)
    )
    if department_code:
        query = query.join(
            Department, Issue.department_id == Department.id
        ).where(Department.code == department_code)

    rows = db.execute(query).all()

    now = datetime.now(timezone.utc)
    cases = []
    for issue, citizen_count in rows:
        created = issue.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days_open = max((now - created).days, 0)

        priority = round(
            SEVERITY_WEIGHTS[issue.category] * citizen_count * (1 + days_open / 7), 1
        )
        cases.append(
            {
                "issue": issue,
                "citizen_count": citizen_count,
                "days_open": days_open,
                "priority_score": priority,
                "department_code": issue.department.code if issue.department else None,
                "department_name": issue.department.name if issue.department else None,
            }
        )

    cases.sort(key=lambda case: case["priority_score"], reverse=True)
    return cases


def list_departments(db: Session) -> list[dict]:
    open_cases = func.count(Issue.id)
    rows = db.execute(
        select(Department, open_cases)
        .outerjoin(
            Issue,
            and_(
                Issue.department_id == Department.id,
                Issue.is_primary.is_(True),
                Issue.status.notin_(CLOSED_STATUSES),
            ),
        )
        .group_by(Department.id)
        .order_by(Department.name)
    ).all()
    return [
        {
            "code": department.code,
            "name": department.name,
            "email": department.email,
            "open_cases": count,
        }
        for department, count in rows
    ]


def _get_issue_or_404(db: Session, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


def update_issue(db: Session, issue_id: int, data: IssueUpdate) -> Issue:
    issue = _get_issue_or_404(db, issue_id)

    updates = data.model_dump(exclude_unset=True)
    old_status = issue.status
    for field, value in updates.items():
        setattr(issue, field, value)

    status_changed = issue.status != old_status
    note = updates.get("resolution_note") or ""
    if status_changed or note:
        record_status_change(
            db,
            issue,
            old_status=old_status,
            new_status=issue.status,
            note=note,
            role=Role.ADMIN,
        )

    db.commit()
    db.refresh(issue)
    return issue


def save_resolution_proof(
    db: Session,
    issue_id: int,
    *,
    content: bytes,
    extension: str,
    storage: Storage | None = None,
) -> Issue:
    issue = _get_issue_or_404(db, issue_id)

    storage = storage or get_storage()
    photo_url = storage.save(
        content=content, extension=extension, prefix="resolutions"
    )
    issue.resolution_photo_url = photo_url
    record_status_change(
        db,
        issue,
        old_status=issue.status,
        new_status=issue.status,
        note="Proof of resolution uploaded.",
        photo_url=photo_url,
        role=Role.ADMIN,
    )

    db.commit()
    db.refresh(issue)
    return issue


def delete_issue(db: Session, issue_id: int) -> None:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    db.delete(issue)
    db.commit()

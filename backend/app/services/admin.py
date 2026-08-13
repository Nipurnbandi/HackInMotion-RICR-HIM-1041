from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.issue_types import CLOSED_STATUSES, SEVERITY_WEIGHTS
from app.core.roles import Role
from app.models import Issue, User
from app.schemas.admin import IssueUpdate


def get_admin_dashboard(db: Session, user: User) -> dict:
    total_issues = db.query(Issue).filter(Issue.is_primary.is_(True)).count()
    total_citizens = db.query(User).filter(User.role == Role.CITIZEN).count()
    return {
        "message": "Welcome to the Admin Dashboard.",
        "role": user.role.value,
        "total_issues": total_issues,
        "total_citizens": total_citizens,
    }


def get_admin_analytics(db: Session) -> dict:
    primaries = db.query(Issue).filter(Issue.is_primary.is_(True))
    total_issues = primaries.count()
    open_issues = primaries.filter(Issue.status.notin_(CLOSED_STATUSES)).count()
    closed_issues = primaries.filter(Issue.status.in_(CLOSED_STATUSES)).count()
    total_citizens = db.query(User).filter(User.role == Role.CITIZEN).count()
    return {
        "total_issues": total_issues,
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "total_citizens": total_citizens,
    }


def list_admin_cases(db: Session) -> list[dict]:
    member = aliased(Issue)
    citizens = func.count(func.distinct(member.citizen_id))

    rows = db.execute(
        select(Issue, citizens)
        .join(member, member.case_id == Issue.case_id)
        .where(Issue.is_primary.is_(True))
        .group_by(Issue.id)
    ).all()

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
            }
        )

    cases.sort(key=lambda case: case["priority_score"], reverse=True)
    return cases


def update_issue(db: Session, issue_id: int, data: IssueUpdate) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(issue, field, value)

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

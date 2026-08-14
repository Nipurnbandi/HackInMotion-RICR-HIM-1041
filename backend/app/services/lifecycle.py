from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.issue_types import IssueStatus
from app.core.roles import Role
from app.models import Issue, StatusHistory


def record_status_change(
    db: Session,
    issue: Issue,
    *,
    old_status: IssueStatus | None,
    new_status: IssueStatus,
    note: str = "",
    photo_url: str | None = None,
    role: Role,
) -> StatusHistory:
    entry = StatusHistory(
        issue_id=issue.id,
        old_status=old_status,
        new_status=new_status,
        note=note,
        photo_url=photo_url,
        changed_by_role=role,
    )
    db.add(entry)
    return entry


def case_primary(db: Session, issue: Issue) -> Issue:
    """The issue that carries the case's status — the primary of its case."""
    if issue.is_primary or not issue.case_id:
        return issue
    primary = db.scalar(
        select(Issue)
        .where(Issue.case_id == issue.case_id, Issue.is_primary.is_(True))
        .limit(1)
    )
    return primary or issue


def list_issue_history(db: Session, issue: Issue) -> list[StatusHistory]:
    """Case-level trail: the primary's history plus this report's own entries."""
    issue_ids = {issue.id, case_primary(db, issue).id}
    return list(
        db.scalars(
            select(StatusHistory)
            .where(StatusHistory.issue_id.in_(issue_ids))
            .order_by(StatusHistory.created_at.asc(), StatusHistory.id.asc())
        )
    )


def _require_resolved(primary: Issue, action: str) -> None:
    if primary.status != IssueStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only resolved reports can be {action}.",
        )


def confirm_resolution(db: Session, issue: Issue) -> Issue:
    primary = case_primary(db, issue)
    _require_resolved(primary, "confirmed")
    record_status_change(
        db,
        primary,
        old_status=IssueStatus.RESOLVED,
        new_status=IssueStatus.RESOLVED,
        note="Reporter confirmed the problem is fixed.",
        role=Role.CITIZEN,
    )
    db.commit()
    db.refresh(issue)
    return issue


def reopen_issue(db: Session, issue: Issue) -> Issue:
    primary = case_primary(db, issue)
    _require_resolved(primary, "reopened")
    record_status_change(
        db,
        primary,
        old_status=IssueStatus.RESOLVED,
        new_status=IssueStatus.UNDER_REVIEW,
        note="Reporter reopened the report — the problem is not fixed.",
        role=Role.CITIZEN,
    )
    primary.status = IssueStatus.UNDER_REVIEW
    db.commit()
    db.refresh(issue)
    return issue

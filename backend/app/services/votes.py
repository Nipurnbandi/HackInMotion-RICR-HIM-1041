from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Issue, IssueVote, User


def vote_counts(db: Session) -> dict[int, int]:
    """Votes per primary issue id."""
    rows = db.execute(
        select(IssueVote.issue_id, func.count(IssueVote.id)).group_by(
            IssueVote.issue_id
        )
    ).all()
    return {issue_id: count for issue_id, count in rows}


def voted_issue_ids(db: Session, user: User) -> set[int]:
    rows = db.execute(
        select(IssueVote.issue_id).where(IssueVote.citizen_id == user.id)
    ).all()
    return {issue_id for (issue_id,) in rows}


def toggle_vote(db: Session, user: User, issue_id: int) -> dict:
    issue = db.get(Issue, issue_id)
    if issue is None or not issue.is_primary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    reported_it = (
        db.query(Issue)
        .filter(Issue.case_id == issue.case_id, Issue.citizen_id == user.id)
        .first()
    )
    if reported_it is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You reported this problem — your report already counts.",
        )

    existing = (
        db.query(IssueVote)
        .filter(IssueVote.issue_id == issue.id, IssueVote.citizen_id == user.id)
        .first()
    )
    if existing is not None:
        db.delete(existing)
        has_voted = False
    else:
        db.add(IssueVote(issue_id=issue.id, citizen_id=user.id))
        has_voted = True
    db.commit()

    count = (
        db.query(IssueVote).filter(IssueVote.issue_id == issue.id).count()
    )
    return {"issue_id": issue.id, "vote_count": count, "has_voted": has_voted}

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.issue_types import IssueStatus
from app.core.roles import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Issue, User
from app.schemas.auth import SignupRequest
from app.schemas.issue import IssueUpdate


def signup_user(db: Session, data: SignupRequest) -> User:
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=Role.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user


def issue_access_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role.value)


def create_admin_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=Role.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_admin_dashboard(db: Session, user: User) -> dict:
    # Primaries only: one real-world problem counts once, however many
    # citizens reported it.
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
    closed_statuses = (IssueStatus.RESOLVED, IssueStatus.REJECTED)
    open_issues = primaries.filter(Issue.status.notin_(closed_statuses)).count()
    closed_issues = primaries.filter(Issue.status.in_(closed_statuses)).count()
    total_citizens = db.query(User).filter(User.role == Role.CITIZEN).count()
    return {
        "total_issues": total_issues,
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "total_citizens": total_citizens,
    }


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

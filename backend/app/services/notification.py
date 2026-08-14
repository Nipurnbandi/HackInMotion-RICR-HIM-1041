from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.issue_types import CATEGORY_LABELS
from app.core.notifier import get_notifier
from app.models import Department, Issue, Notification


def build_message(issue: Issue, department: Department) -> str:
    location = issue.address or f"{issue.latitude}, {issue.longitude}"
    return (
        f"A new problem has been assigned to {department.name}.\n\n"
        f"Category: {CATEGORY_LABELS[issue.category]}\n"
        f"Case: {issue.case_id}\n"
        f"Location: {location}\n"
        f"Description: {issue.description}\n\n"
        f"Open your department queue to review it."
    )


def notify_new_case(db: Session, issue: Issue) -> Notification | None:
    if issue.department_id is None:
        return None

    department = db.get(Department, issue.department_id)
    notification = Notification(
        department_id=department.id,
        issue_id=issue.id,
        message=build_message(issue, department),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_pending_notifications() -> None:
    db = SessionLocal()
    try:
        notifier = get_notifier()
        pending = (
            db.query(Notification).filter(Notification.sent_at.is_(None)).all()
        )
        for notification in pending:
            department = db.get(Department, notification.department_id)
            issue = db.get(Issue, notification.issue_id)
            case_id = issue.case_id if issue else "unknown"
            try:
                notifier.send(
                    to=department.email,
                    subject=f"[SmartCity] New case {case_id} for {department.name}",
                    body=notification.message,
                )
                notification.sent_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()


def list_notifications(
    db: Session, *, limit: int = 50
) -> tuple[list[tuple[Notification, Department]], int]:
    rows = (
        db.query(Notification, Department)
        .join(Department, Notification.department_id == Department.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )
    unread = db.query(Notification).filter(Notification.is_read.is_(False)).count()
    return rows, unread


def mark_notification_read(db: Session, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification

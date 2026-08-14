from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.issue_types import CATEGORY_LABELS, CLOSED_STATUSES, SLA_DAYS
from app.core.roles import Role
from app.models import Department, Issue, Notification
from app.services.lifecycle import record_status_change

# Breached cases escalate to this department — the "higher authority".
ESCALATION_DEPARTMENT_CODE = "GENERAL"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def sla_deadline(issue: Issue) -> datetime:
    return _as_utc(issue.created_at) + timedelta(days=SLA_DAYS[issue.category])


def _escalation_message(issue: Issue, department: Department | None) -> str:
    location = issue.address or f"{issue.latitude}, {issue.longitude}"
    owner = department.name if department else "an unassigned queue"
    return (
        f"SLA BREACH — case escalated to higher authority.\n\n"
        f"Category: {CATEGORY_LABELS[issue.category]}\n"
        f"Case: {issue.case_id}\n"
        f"Location: {location}\n"
        f"Owned by: {owner}\n"
        f"SLA limit: {SLA_DAYS[issue.category]} days — exceeded.\n\n"
        f"This case has waited too long and now needs senior attention."
    )


def run_sla_escalations(db: Session, *, now: datetime | None = None) -> list[Issue]:
    """Escalate open cases that breached their category SLA. Idempotent —
    each case escalates once, is flagged, logged in its history, and the
    higher authority (General Administration) is notified."""
    now = now or datetime.now(timezone.utc)

    candidates = (
        db.query(Issue)
        .filter(
            Issue.is_primary.is_(True),
            Issue.status.notin_(CLOSED_STATUSES),
            Issue.escalated_at.is_(None),
        )
        .all()
    )
    overdue = [issue for issue in candidates if now >= sla_deadline(issue)]
    if not overdue:
        return []

    higher_authority = (
        db.query(Department)
        .filter(Department.code == ESCALATION_DEPARTMENT_CODE)
        .first()
    )

    for issue in overdue:
        issue.escalated_at = now
        record_status_change(
            db,
            issue,
            old_status=issue.status,
            new_status=issue.status,
            note=(
                f"Escalated to higher authority — unresolved beyond the "
                f"{SLA_DAYS[issue.category]}-day SLA for "
                f"{CATEGORY_LABELS[issue.category]}."
            ),
            role=Role.ADMIN,
        )
        if higher_authority is not None:
            db.add(
                Notification(
                    department_id=higher_authority.id,
                    issue_id=issue.id,
                    message=_escalation_message(issue, issue.department),
                )
            )

    db.commit()
    return overdue

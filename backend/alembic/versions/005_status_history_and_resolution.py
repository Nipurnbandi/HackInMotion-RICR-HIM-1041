"""Status history and resolution evidence

Revision ID: 005_status_history
Revises: 004_departments
Create Date: 2026-08-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_status_history"
down_revision: Union[str, None] = "004_departments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_ENUM = sa.Enum(
    "SUBMITTED",
    "UNDER_REVIEW",
    "IN_PROGRESS",
    "RESOLVED",
    "REJECTED",
    name="issue_status",
    native_enum=False,
)

ROLE_ENUM = sa.Enum("CITIZEN", "ADMIN", name="role", native_enum=False)


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column("resolution_note", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "issues",
        sa.Column("resolution_photo_url", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("old_status", STATUS_ENUM, nullable=True),
        sa.Column("new_status", STATUS_ENUM, nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("changed_by_role", ROLE_ENUM, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_status_history_issue_id"), "status_history", ["issue_id"]
    )

    # Backfill: every existing issue gets a creation entry so timelines are complete.
    op.execute(
        "INSERT INTO status_history "
        "(issue_id, old_status, new_status, note, changed_by_role, created_at, updated_at) "
        "SELECT id, NULL, 'SUBMITTED', 'Report submitted.', 'CITIZEN', created_at, created_at "
        "FROM issues"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_status_history_issue_id"), table_name="status_history")
    op.drop_table("status_history")
    op.drop_column("issues", "resolution_photo_url")
    op.drop_column("issues", "resolution_note")

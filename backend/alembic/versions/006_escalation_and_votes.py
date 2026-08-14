"""SLA escalation timestamp and citizen upvotes

Revision ID: 006_escalation_votes
Revises: 005_status_history
Create Date: 2026-08-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_escalation_votes"
down_revision: Union[str, None] = "005_status_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "issue_votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("citizen_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["citizen_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issue_id", "citizen_id", name="uq_issue_votes_issue_citizen"
        ),
    )
    op.create_index(op.f("ix_issue_votes_issue_id"), "issue_votes", ["issue_id"])
    op.create_index(op.f("ix_issue_votes_citizen_id"), "issue_votes", ["citizen_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_issue_votes_citizen_id"), table_name="issue_votes")
    op.drop_index(op.f("ix_issue_votes_issue_id"), table_name="issue_votes")
    op.drop_table("issue_votes")
    op.drop_column("issues", "escalated_at")

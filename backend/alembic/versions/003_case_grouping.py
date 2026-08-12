"""Case grouping for duplicate reports

Adds case_id + is_primary to issues. Every existing report is backfilled as
its own case (a case of one), so no data changes meaning.

Revision ID: 003_case_grouping
Revises: 002_civic_issue
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_case_grouping"
down_revision: Union[str, None] = "002_civic_issue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("issues", sa.Column("case_id", sa.String(length=32), nullable=True))
    op.add_column(
        "issues",
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )
    op.create_index(op.f("ix_issues_case_id"), "issues", ["case_id"])
    op.create_index(
        "ix_issues_dup_lookup", "issues", ["category", "latitude", "longitude"]
    )

    # Backfill: every pre-existing report becomes the primary of its own case.
    op.execute(
        "UPDATE issues SET case_id = 'CASE-' || LPAD(id::text, 6, '0') "
        "WHERE case_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_issues_dup_lookup", table_name="issues")
    op.drop_index(op.f("ix_issues_case_id"), table_name="issues")
    op.drop_column("issues", "is_primary")
    op.drop_column("issues", "case_id")

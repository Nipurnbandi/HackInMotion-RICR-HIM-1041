"""AI photo verification verdicts

Revision ID: 007_photo_verification
Revises: 006_escalation_votes
Create Date: 2026-08-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_photo_verification"
down_revision: Union[str, None] = "006_escalation_votes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "issues", sa.Column("photo_verdict", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "issues",
        sa.Column("photo_verdict_note", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "issues",
        sa.Column(
            "resolution_photo_verdict", sa.String(length=20), nullable=True
        ),
    )
    op.add_column(
        "issues",
        sa.Column(
            "resolution_photo_verdict_note",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("issues", "resolution_photo_verdict_note")
    op.drop_column("issues", "resolution_photo_verdict")
    op.drop_column("issues", "photo_verdict_note")
    op.drop_column("issues", "photo_verdict")

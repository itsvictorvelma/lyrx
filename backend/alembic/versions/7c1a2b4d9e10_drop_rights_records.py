"""drop rights records

Revision ID: 7c1a2b4d9e10
Revises: 55e38f5fefd5
Create Date: 2026-10-22 21:02:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c1a2b4d9e10"
down_revision: Union[str, Sequence[str], None] = "55e38f5fefd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_rights_records_track_id"), table_name="rights_records")
    op.drop_table("rights_records")


def downgrade() -> None:
    op.create_table(
        "rights_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.String(length=80), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("rightsholder", sa.String(length=300), nullable=False),
        sa.Column("permitted_use", sa.String(length=300), nullable=False),
        sa.Column("territory", sa.String(length=120), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("evidence_reference", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rights_records_track_id"), "rights_records", ["track_id"], unique=False)

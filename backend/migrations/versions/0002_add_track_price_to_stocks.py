"""Add track_price column to stocks

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stocks",
        sa.Column("track_price", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("idx_stocks_track_price", "stocks", ["track_price"])


def downgrade() -> None:
    op.drop_index("idx_stocks_track_price", table_name="stocks")
    op.drop_column("stocks", "track_price")

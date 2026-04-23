"""Add dividend_type and shares_received to dividends

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-23
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # dividend_type: CASH (default) | STOCK | DRIP
    op.add_column(
        "dividends",
        sa.Column(
            "dividend_type",
            sa.String(10),
            nullable=False,
            server_default="CASH",
        ),
    )
    # shares_received: only set for STOCK and DRIP types
    op.add_column(
        "dividends",
        sa.Column("shares_received", sa.Numeric(18, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dividends", "shares_received")
    op.drop_column("dividends", "dividend_type")

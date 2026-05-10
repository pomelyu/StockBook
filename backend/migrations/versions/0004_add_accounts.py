"""Add accounts table and account_id to transactions and dividends

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-06
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create accounts table
    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("market", sa.String(5), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Add account_id as nullable first (required before data migration)
    op.add_column("transactions", sa.Column("account_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_account_id",
        "transactions", "accounts",
        ["account_id"], ["id"],
        ondelete="RESTRICT",
    )

    op.add_column("dividends", sa.Column("account_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_dividends_account_id",
        "dividends", "accounts",
        ["account_id"], ["id"],
        ondelete="RESTRICT",
    )

    # 3. Data migration: create default accounts per user, assign all existing rows
    conn = op.get_bind()

    users = conn.execute(text("SELECT id FROM users")).fetchall()
    for (user_id,) in users:
        tw_id = conn.execute(
            text(
                "INSERT INTO accounts (id, user_id, name, market) "
                "VALUES (gen_random_uuid(), :uid, 'TW-預設', 'TW') RETURNING id"
            ),
            {"uid": user_id},
        ).scalar()

        us_id = conn.execute(
            text(
                "INSERT INTO accounts (id, user_id, name, market) "
                "VALUES (gen_random_uuid(), :uid, 'US-預設', 'US') RETURNING id"
            ),
            {"uid": user_id},
        ).scalar()

        # Transactions: .TW / .TWO tickers → TW-預設, everything else → US-預設
        conn.execute(
            text(
                "UPDATE transactions SET account_id = :tw_id "
                "WHERE user_id = :uid AND stock_id IN ("
                "  SELECT id FROM stocks WHERE ticker LIKE '%.TW' OR ticker LIKE '%.TWO'"
                ")"
            ),
            {"tw_id": tw_id, "uid": user_id},
        )
        conn.execute(
            text(
                "UPDATE transactions SET account_id = :us_id "
                "WHERE user_id = :uid AND account_id IS NULL"
            ),
            {"us_id": us_id, "uid": user_id},
        )

        # Dividends: same rule
        conn.execute(
            text(
                "UPDATE dividends SET account_id = :tw_id "
                "WHERE user_id = :uid AND stock_id IN ("
                "  SELECT id FROM stocks WHERE ticker LIKE '%.TW' OR ticker LIKE '%.TWO'"
                ")"
            ),
            {"tw_id": tw_id, "uid": user_id},
        )
        conn.execute(
            text(
                "UPDATE dividends SET account_id = :us_id "
                "WHERE user_id = :uid AND account_id IS NULL"
            ),
            {"us_id": us_id, "uid": user_id},
        )

    # 4. Tighten to NOT NULL now that every row has been assigned
    op.alter_column("transactions", "account_id", nullable=False)
    op.alter_column("dividends", "account_id", nullable=False)


def downgrade() -> None:
    op.alter_column("transactions", "account_id", nullable=True)
    op.alter_column("dividends", "account_id", nullable=True)
    op.drop_constraint("fk_dividends_account_id", "dividends", type_="foreignkey")
    op.drop_column("dividends", "account_id")
    op.drop_constraint("fk_transactions_account_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "account_id")
    op.drop_table("accounts")

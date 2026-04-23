"""Transaction business logic.

Handles SELL validation (position check) and FIFO-safe create/update/delete.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def get_position(
    user_id: uuid.UUID,
    stock_id: uuid.UUID,
    db: AsyncSession,
    exclude_tx_id: uuid.UUID | None = None,
) -> Decimal:
    """Return current share position = sum(BUY qty) - sum(SELL qty).

    Pass ``exclude_tx_id`` when re-validating after an UPDATE so the
    transaction being replaced is not counted twice.
    """
    buy_q = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.stock_id == stock_id,
        Transaction.transaction_type == "BUY",
    )
    sell_q = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.stock_id == stock_id,
        Transaction.transaction_type == "SELL",
    )

    if exclude_tx_id is not None:
        buy_q = buy_q.where(Transaction.id != exclude_tx_id)
        sell_q = sell_q.where(Transaction.id != exclude_tx_id)

    buy_total = Decimal(str(await db.scalar(buy_q) or 0))
    sell_total = Decimal(str(await db.scalar(sell_q) or 0))
    return buy_total - sell_total


async def validate_sell(
    user_id: uuid.UUID,
    stock_id: uuid.UUID,
    quantity: Decimal,
    db: AsyncSession,
    exclude_tx_id: uuid.UUID | None = None,
) -> None:
    """Raise ValueError if selling ``quantity`` would exceed current position."""
    position = await get_position(user_id, stock_id, db, exclude_tx_id=exclude_tx_id)
    if quantity > position:
        raise ValueError(
            f"Insufficient position: have {position}, attempting to sell {quantity}"
        )

"""Transactions CRUD endpoints."""

import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.transaction import TransactionCreate
from app.schemas.transaction import TransactionResponse
from app.schemas.transaction import TransactionUpdate
from app.services.stock_service import get_or_create_stock
from app.services.transaction_service import validate_sell

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_response(tx: Transaction) -> TransactionResponse:
    stock: Stock = tx.stock
    return TransactionResponse(
        id=tx.id,
        ticker=stock.ticker,
        stock_name=stock.name,
        transaction_type=tx.transaction_type,
        quantity=tx.quantity,
        price=tx.price,
        fee=tx.fee,
        transaction_date=tx.transaction_date,
        note=tx.note,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


@router.get(
    "/",
    response_model=Page[TransactionResponse],
    summary="List transactions",
    response_description="分頁的交易紀錄清單",
)
async def list_transactions(
    ticker: str | None = Query(None, description="過濾指定股票代號（大小寫不敏感）"),
    transaction_type: str | None = Query(None, description="過濾交易類型：BUY 或 SELL"),
    page: int = Query(1, ge=1, description="頁碼（從 1 開始）"),
    page_size: int = Query(20, ge=1, le=100, description="每頁筆數（最大 100）"),
    include_all: bool = Query(False, description="若為 True，忽略分頁回傳所有紀錄（前端 P&L 計算用）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得目前登入使用者的交易紀錄，支援分頁與過濾。

    - `ticker`：只回傳指定股票的紀錄（例：`2330.TW` 或 `AAPL`）
    - `transaction_type`：只回傳 BUY 或 SELL
    - `include_all=true`：忽略分頁，回傳全部紀錄（前端 FIFO 計算使用）
    - 結果依 `transaction_date` 升序排列（FIFO 計算需要時序正確）
    """
    base_q = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .options(selectinload(Transaction.stock))
    )

    if ticker:
        base_q = base_q.join(Transaction.stock).where(Stock.ticker == ticker.upper())
    if transaction_type:
        base_q = base_q.where(Transaction.transaction_type == transaction_type.upper())

    total = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    )
    ordered_q = base_q.order_by(Transaction.transaction_date.asc())
    if include_all:
        result = await db.execute(ordered_q)
    else:
        result = await db.execute(
            ordered_q.offset((page - 1) * page_size).limit(page_size)
        )
    items = [_to_response(tx) for tx in result.scalars().all()]
    return Page(items=items, total=total or 0, page=page, page_size=page_size)


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transaction",
    response_description="新建立的交易紀錄",
)
async def create_transaction(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    新增一筆買賣交易紀錄。

    - 台股輸入純數字即可（`2330` 自動轉為 `2330.TW`）
    - **SELL** 交易：若賣出數量超過目前持倉將回傳 **422**
    - 新增後該股票的 `track_price` 設為 `True`，scheduler 開始追蹤其股價
    """
    stock = await get_or_create_stock(body.ticker, db)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticker not found")

    if body.transaction_type == "SELL":
        try:
            await validate_sell(current_user.id, stock.id, body.quantity, db)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if not stock.track_price:
        stock.track_price = True

    tx = Transaction(
        user_id=current_user.id,
        stock_id=stock.id,
        transaction_type=body.transaction_type,
        quantity=body.quantity,
        price=body.price,
        fee=body.fee,
        transaction_date=body.transaction_date,
        note=body.note,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx, ["stock"])
    return _to_response(tx)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction",
    response_description="交易紀錄詳情",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得單筆交易紀錄詳情。

    - 只能存取自己的紀錄，他人的紀錄回傳 **404**
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .options(selectinload(Transaction.stock))
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _to_response(tx)


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    response_description="更新後的交易紀錄",
)
async def update_transaction(
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    修改一筆交易紀錄。只傳入需要修改的欄位，其餘保持不變。

    - 修改後若持倉會變成負數（例：提高 SELL 數量），回傳 **422**
    - 只能修改自己的紀錄
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .options(selectinload(Transaction.stock))
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Apply updates
    if body.transaction_type is not None:
        tx.transaction_type = body.transaction_type
    if body.quantity is not None:
        tx.quantity = body.quantity
    if body.price is not None:
        tx.price = body.price
    if body.fee is not None:
        tx.fee = body.fee
    if body.transaction_date is not None:
        tx.transaction_date = body.transaction_date
    if body.note is not None:
        tx.note = body.note

    # Re-validate if the result is a SELL
    if tx.transaction_type == "SELL":
        try:
            await validate_sell(
                current_user.id, tx.stock_id, tx.quantity, db, exclude_tx_id=tx.id
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    # Re-fetch with selectinload to avoid lazy-load issues on already-loaded relationship
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(selectinload(Transaction.stock))
    )
    tx = result.scalar_one()
    return _to_response(tx)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transaction",
)
async def delete_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刪除一筆交易紀錄。

    - 刪除後若剩餘持倉會變成負數（例如：刪除一筆 BUY 但後續有 SELL），回傳 **422**
    - 只能刪除自己的紀錄
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == current_user.id
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Validate that deleting this BUY won't leave existing SELLs uncovered.
    # Logic: after deletion, new_position = current_position - this_buy_qty.
    # If current_position < this_buy_qty, new_position < 0 → reject.
    # Equivalent to: validate_sell(this_buy_qty) against current_position (without excluding self).
    if tx.transaction_type == "BUY":
        try:
            await validate_sell(current_user.id, tx.stock_id, tx.quantity, db)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot delete: removing this BUY would result in negative position",
            )

    await db.delete(tx)
    await db.commit()

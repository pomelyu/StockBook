"""Dividends CRUD endpoints."""

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
from app.models.dividend import Dividend
from app.models.stock import Stock
from app.models.user import User
from app.schemas.dividend import DividendCreate
from app.schemas.dividend import DividendResponse
from app.schemas.dividend import DividendUpdate
from app.schemas.pagination import Page
from app.services.stock_service import get_or_create_stock

router = APIRouter(prefix="/dividends", tags=["dividends"])


def _to_response(div: Dividend) -> DividendResponse:
    stock: Stock = div.stock
    return DividendResponse(
        id=div.id,
        ticker=stock.ticker,
        stock_name=stock.name,
        dividend_type=div.dividend_type,
        amount=div.amount,
        currency=div.currency,
        shares_received=div.shares_received,
        ex_dividend_date=div.ex_dividend_date,
        payment_date=div.payment_date,
        note=div.note,
        created_at=div.created_at,
    )


@router.get(
    "/",
    response_model=Page[DividendResponse],
    summary="List dividends",
    response_description="分頁的股息紀錄清單",
)
async def list_dividends(
    ticker: str | None = Query(None, description="過濾指定股票代號（大小寫不敏感）"),
    page: int = Query(1, ge=1, description="頁碼（從 1 開始）"),
    page_size: int = Query(20, ge=1, le=100, description="每頁筆數（最大 100）"),
    include_all: bool = Query(False, description="若為 True，忽略分頁回傳所有紀錄（前端 P&L 計算用）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得目前登入使用者的股息紀錄，支援分頁與過濾。

    - `ticker`：只回傳指定股票的股息紀錄
    - `include_all=true`：忽略分頁，回傳全部紀錄（前端 FIFO 計算使用）
    - 結果依 `ex_dividend_date` 升序排列（FIFO 計算需要時序正確）
    - `dividend_type` 為 CASH（現金股息）、STOCK（配股）、DRIP（股息再投入）
    """
    base_q = (
        select(Dividend)
        .where(Dividend.user_id == current_user.id)
        .options(selectinload(Dividend.stock))
    )

    if ticker:
        base_q = base_q.join(Dividend.stock).where(Stock.ticker == ticker.upper())

    total = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    )
    ordered_q = base_q.order_by(Dividend.ex_dividend_date.asc())
    if include_all:
        result = await db.execute(ordered_q)
    else:
        result = await db.execute(
            ordered_q.offset((page - 1) * page_size).limit(page_size)
        )
    items = [_to_response(d) for d in result.scalars().all()]
    return Page(items=items, total=total or 0, page=page, page_size=page_size)


@router.post(
    "/",
    response_model=DividendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create dividend record",
    response_description="新建立的股息紀錄",
)
async def create_dividend(
    body: DividendCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    新增一筆股息紀錄。

    - **CASH**：現金股息，填入實際收到的金額
    - **STOCK**：配股（股票股息），`amount` 填 0，`shares_received` 填取得股數
    - **DRIP**：股息再投入，`amount` 填再投入金額，`shares_received` 填取得股數
    - STOCK / DRIP 類型在 P&L 計算時會以零成本（STOCK）或 amount÷shares 成本（DRIP）加入 FIFO 佇列
    - 台股輸入純數字即可（`2330` 自動轉為 `2330.TW`）
    """
    stock = await get_or_create_stock(body.ticker, db)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticker not found")

    div = Dividend(
        user_id=current_user.id,
        stock_id=stock.id,
        dividend_type=body.dividend_type,
        amount=body.amount,
        currency=body.currency,
        shares_received=body.shares_received,
        ex_dividend_date=body.ex_dividend_date,
        payment_date=body.payment_date,
        note=body.note,
    )
    db.add(div)
    await db.commit()
    await db.refresh(div, ["stock"])
    return _to_response(div)


@router.get(
    "/{dividend_id}",
    response_model=DividendResponse,
    summary="Get dividend record",
    response_description="股息紀錄詳情",
)
async def get_dividend(
    dividend_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得單筆股息紀錄詳情。

    - 只能存取自己的紀錄，他人的紀錄回傳 **404**
    """
    result = await db.execute(
        select(Dividend)
        .where(Dividend.id == dividend_id, Dividend.user_id == current_user.id)
        .options(selectinload(Dividend.stock))
    )
    div = result.scalar_one_or_none()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dividend not found")
    return _to_response(div)


@router.put(
    "/{dividend_id}",
    response_model=DividendResponse,
    summary="Update dividend record",
    response_description="更新後的股息紀錄",
)
async def update_dividend(
    dividend_id: uuid.UUID,
    body: DividendUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    修改一筆股息紀錄。只傳入需要修改的欄位，其餘保持不變。

    - 只能修改自己的紀錄
    """
    result = await db.execute(
        select(Dividend)
        .where(Dividend.id == dividend_id, Dividend.user_id == current_user.id)
        .options(selectinload(Dividend.stock))
    )
    div = result.scalar_one_or_none()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dividend not found")

    if body.dividend_type is not None:
        div.dividend_type = body.dividend_type
    if body.amount is not None:
        div.amount = body.amount
    if body.currency is not None:
        div.currency = body.currency
    if body.shares_received is not None:
        div.shares_received = body.shares_received
    if body.ex_dividend_date is not None:
        div.ex_dividend_date = body.ex_dividend_date
    if body.payment_date is not None:
        div.payment_date = body.payment_date
    if body.note is not None:
        div.note = body.note

    await db.commit()
    await db.refresh(div, ["stock"])
    return _to_response(div)


@router.delete(
    "/{dividend_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dividend record",
)
async def delete_dividend(
    dividend_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刪除一筆股息紀錄。

    - 只能刪除自己的紀錄
    """
    result = await db.execute(
        select(Dividend).where(
            Dividend.id == dividend_id, Dividend.user_id == current_user.id
        )
    )
    div = result.scalar_one_or_none()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dividend not found")

    await db.delete(div)
    await db.commit()

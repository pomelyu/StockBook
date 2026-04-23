from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistAddRequest
from app.schemas.watchlist import WatchlistItemResponse
from app.services.stock_service import get_or_create_stock

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _to_response(entry: Watchlist) -> WatchlistItemResponse:  # noqa: D401
    stock: Stock = entry.stock
    return WatchlistItemResponse(
        id=entry.id,
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        currency=stock.currency,
        last_price=stock.last_price,
        price_updated_at=stock.price_updated_at,
        note=entry.note,
        added_at=entry.added_at,
    )


@router.get(
    "/",
    response_model=list[WatchlistItemResponse],
    summary="List watchlist",
    response_description="目前使用者的自選股清單，依加入時間降序排列",
)
async def list_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得目前登入使用者的自選股清單。

    - 每筆資料包含股票基本資訊與最新快取股價（`last_price`）
    - 股價由 scheduler 定期更新，`price_updated_at` 為最後更新時間
    - 尚未有快取股價時 `last_price` 為 null
    """
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == current_user.id)
        .options(selectinload(Watchlist.stock))
        .order_by(Watchlist.added_at.desc())
    )
    entries = result.scalars().all()
    return [_to_response(e) for e in entries]


@router.post(
    "/",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add stock to watchlist",
    response_description="新增的 watchlist 項目",
)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    將指定股票加入自選股清單。

    - 台股輸入純數字即可（`2330` 自動轉為 `2330.TW`）
    - 若股票不在 DB catalog 中，會嘗試透過 yfinance 建立（首次加入時可能較慢）
    - 加入後該股票的 `track_price` 設為 `True`，scheduler 開始定期更新其股價
    - 已在 watchlist 中時回傳 **409**
    - Ticker 無法識別時回傳 **404**
    """
    stock = await get_or_create_stock(body.ticker, db)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticker not found")

    # Ensure the scheduler tracks this stock's price going forward
    if not stock.track_price:
        stock.track_price = True

    # Check for duplicate
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_id == stock.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in watchlist")

    entry = Watchlist(user_id=current_user.id, stock_id=stock.id, note=body.note)
    db.add(entry)
    await db.commit()
    await db.refresh(entry, ["stock"])
    return _to_response(entry)


@router.delete(
    "/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove stock from watchlist",
)
async def remove_from_watchlist(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    將指定股票從自選股清單中移除。

    - `ticker` 大小寫不敏感（自動轉為大寫）
    - 移除後股票的 `track_price` 保持 `True`（若有交易紀錄則仍需繼續追蹤）
    - 不在 watchlist 中時回傳 **404**
    """
    result = await db.execute(
        select(Watchlist)
        .join(Watchlist.stock)
        .where(
            Watchlist.user_id == current_user.id,
            Stock.ticker == ticker.upper(),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in watchlist")

    await db.delete(entry)
    await db.commit()

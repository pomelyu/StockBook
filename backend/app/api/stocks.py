from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import StockResponse
from app.services.stock_service import get_or_create_stock
from app.services.stock_service import search_stocks

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get(
    "/search",
    response_model=list[StockResponse],
    summary="Search stocks",
    response_description="符合搜尋條件的股票列表（最多 10 筆）",
)
async def search(
    q: str = Query(..., min_length=1, description="Ticker 前綴或股票名稱關鍵字，如 2330、AAPL、台積電"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    搜尋股票，優先從 DB 快取查詢。

    - **DB 有資料**：直接回傳，不呼叫外部 API
    - **DB 沒有資料**：fallback 至 yfinance 查詢，查到後寫入 DB 快取再回傳
    - 台股輸入純數字會自動正規化：`2330` → `2330.TW`
    - 無結果時回傳空陣列（不是 404）
    """
    return await search_stocks(q, db)


@router.get(
    "/{ticker}",
    response_model=StockResponse,
    summary="Get stock by ticker",
    response_description="股票基本資料與最新快取股價",
)
async def get_stock(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    依 ticker 取得單一股票資料。

    - **DB 有快取**：直接回傳，不呼叫外部 API
    - **DB 無快取**：呼叫 yfinance 建立快取後回傳
    - `last_price` 由 APScheduler 定期更新（非即時），`price_updated_at` 為最後更新時間
    - ticker 不存在（yfinance 也找不到）時回傳 **404**
    """
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        stock = await get_or_create_stock(ticker, db)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    return stock

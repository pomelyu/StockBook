from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.exchange_rate import ExchangeRate
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import StockResponse
from app.services.stock_service import get_or_create_stock
from app.services.stock_service import search_stocks

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get(
    "/exchange-rate",
    response_model=dict,
    summary="Get latest exchange rate",
    response_description="最新匯率資料",
)
async def get_exchange_rate(
    from_currency: str = Query("USD", description="來源幣別"),
    to_currency: str = Query("TWD", description="目標幣別"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    取得最新的匯率資料（由 APScheduler 定期更新）。

    - 回傳 `rate`（from_currency → to_currency 的換算比率）
    - 若 DB 尚無資料（首次啟動前 scheduler 尚未執行），回傳 **404**
    """
    result = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.from_currency == from_currency.upper())
        .where(ExchangeRate.to_currency == to_currency.upper())
        .order_by(ExchangeRate.fetched_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange rate not found")
    return {
        "from_currency": row.from_currency,
        "to_currency": row.to_currency,
        "rate": float(row.rate),
        "fetched_at": row.fetched_at.isoformat(),
    }


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
    "/prices",
    response_model=dict[str, StockResponse],
    summary="Batch get stock prices",
    response_description="各 ticker 的股票資料與最新快取股價",
)
async def batch_get_prices(
    tickers: str = Query(..., description="逗號分隔的 ticker 列表，如 2330.TW,AAPL,MSFT"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    批次取得多支股票的現價資料。

    - 一次 API call 取得多個 ticker 的 `last_price`，供前端 P&L 計算使用
    - 只回傳 DB 快取中已存在的 ticker，不觸發 yfinance fallback
    - `last_price` 由 APScheduler 定期更新（非即時）
    - 不存在的 ticker 不會出現在回傳結果中
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return {}
    result = await db.execute(select(Stock).where(Stock.ticker.in_(ticker_list)))
    stocks = result.scalars().all()
    return {s.ticker: s for s in stocks}


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

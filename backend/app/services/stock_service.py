"""Stock data fetching and price update logic.

yfinance is synchronous, so all network calls run in a thread pool via
asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio
import logging
from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock

logger = logging.getLogger(__name__)


def _normalize_ticker(ticker: str) -> str:
    """Normalise user input to a yfinance-compatible ticker.

    Pure digits (e.g. "2330") are treated as Taiwan stocks → "2330.TW".
    Everything else is upper-cased and returned as-is.
    Note: TPEX stocks (.TWO) require DB lookup — see get_or_create_stock.
    """
    t = ticker.strip().upper()
    if t.isdigit():
        return f"{t}.TW"
    return t


async def _resolve_tw_ticker(code: str, db: AsyncSession) -> tuple[str, dict | None]:
    """For pure-digit input, resolve the correct .TW or .TWO suffix.

    1. Check catalog DB for .TW then .TWO.
    2. If not in catalog, probe yfinance with .TWO then .TW.
    Returns (ticker, yfinance_info_or_None).
    """
    for suffix in (".TW", ".TWO"):
        result = await db.execute(select(Stock).where(Stock.ticker == f"{code}{suffix}"))
        if result.scalar_one_or_none() is not None:
            return f"{code}{suffix}", None

    # Not in catalog — probe yfinance to find the correct suffix
    for suffix in (".TWO", ".TW"):
        candidate = f"{code}{suffix}"
        info = await asyncio.to_thread(_fetch_stock_info_sync, candidate)
        if info is not None:
            return candidate, info

    return f"{code}.TW", None


def _infer_market_currency(ticker: str) -> tuple[str, str]:
    """Return (market, currency) from a normalised ticker."""
    if ticker.endswith(".TW") or ticker.endswith(".TWO"):
        return "TW", "TWD"
    return "US", "USD"


def _fetch_stock_info_sync(ticker: str) -> dict | None:
    """Fetch basic stock info from yfinance (blocking)."""
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info
        if not info or info.get("trailingPegRatio") is None and info.get("symbol") is None:
            # yfinance returns a sparse dict for invalid tickers
            return None
        return info
    except Exception as exc:
        logger.warning("yfinance info fetch failed for %s: %s", ticker, exc)
        return None


def _fetch_prices_sync(tickers: list[str]) -> dict[str, float]:
    """Batch-fetch latest closing prices (blocking).

    Returns {ticker: price} for tickers where data was available.
    """
    if not tickers:
        return {}

    try:
        import yfinance as yf

        if len(tickers) == 1:
            t = yf.Ticker(tickers[0])
            price = t.fast_info.last_price
            if price:
                return {tickers[0]: float(price)}
            return {}

        data = yf.download(
            tickers=tickers,
            period="2d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if data.empty:
            return {}

        prices: dict[str, float] = {}
        close = data["Close"]
        for ticker in tickers:
            try:
                series = close[ticker].dropna() if ticker in close.columns else close.dropna()
                if not series.empty:
                    prices[ticker] = float(series.iloc[-1])
            except Exception:
                pass
        return prices

    except Exception as exc:
        logger.error("yfinance batch price fetch failed: %s", exc)
        return {}


def _fetch_exchange_rate_sync(from_currency: str, to_currency: str) -> float | None:
    """Fetch latest exchange rate from yfinance (blocking)."""
    try:
        import yfinance as yf

        ticker = f"{from_currency}{to_currency}=X"
        rate = yf.Ticker(ticker).fast_info.last_price
        return float(rate) if rate else None
    except Exception as exc:
        logger.warning("Exchange rate fetch failed (%s→%s): %s", from_currency, to_currency, exc)
        return None


async def get_or_create_stock(ticker_raw: str, db: AsyncSession) -> Stock | None:
    """Return an existing Stock or create one after verifying via yfinance."""
    t = ticker_raw.strip().upper()
    prefetched_info: dict | None = None

    if t.isdigit():
        ticker, prefetched_info = await _resolve_tw_ticker(t, db)
    else:
        ticker = _normalize_ticker(ticker_raw)

    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()
    if stock:
        return stock

    info = prefetched_info or await asyncio.to_thread(_fetch_stock_info_sync, ticker)
    market, currency = _infer_market_currency(ticker)

    name: str | None = None
    if info:
        name = info.get("longName") or info.get("shortName")
        # Prefer yfinance currency when available
        yf_currency = info.get("currency")
        if yf_currency:
            currency = yf_currency

    stock = Stock(ticker=ticker, name=name, market=market, currency=currency)
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


async def search_stocks(query: str, db: AsyncSession) -> list[Stock]:
    """Search stocks by ticker prefix or name substring (DB-first, yfinance fallback)."""
    q = query.strip().upper()

    result = await db.execute(
        select(Stock).where(
            Stock.ticker.ilike(f"{q}%") | Stock.name.ilike(f"%{q}%")
        ).limit(10)
    )
    stocks = list(result.scalars().all())
    if stocks:
        return stocks

    # Fallback: try to look up directly on yfinance
    ticker = _normalize_ticker(query)
    stock = await get_or_create_stock(ticker, db)
    return [stock] if stock else []


async def batch_update_prices(db: AsyncSession) -> int:
    """Fetch latest prices for tracked stocks and persist them. Returns update count.

    Only stocks with track_price=True are updated — these are stocks that a user
    has added to their watchlist or holds in a transaction.
    """
    result = await db.execute(select(Stock).where(Stock.track_price.is_(True)))
    stocks: list[Stock] = list(result.scalars().all())
    if not stocks:
        return 0

    tickers = [s.ticker for s in stocks]
    prices = await asyncio.to_thread(_fetch_prices_sync, tickers)

    now = datetime.now(timezone.utc)
    updated = 0
    for stock in stocks:
        price = prices.get(stock.ticker)
        if price is not None:
            stock.last_price = price
            stock.price_updated_at = now
            updated += 1

    await db.commit()
    logger.info("Updated prices for %d/%d stocks", updated, len(stocks))
    return updated


async def update_exchange_rate(from_currency: str, to_currency: str, db: AsyncSession) -> bool:
    """Fetch and persist latest exchange rate. Returns True on success."""
    from app.models.exchange_rate import ExchangeRate

    rate = await asyncio.to_thread(_fetch_exchange_rate_sync, from_currency, to_currency)
    if rate is None:
        return False

    db.add(ExchangeRate(from_currency=from_currency, to_currency=to_currency, rate=rate))
    await db.commit()
    return True

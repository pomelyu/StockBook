"""Stock catalog synchronisation service.

Fetches the full list of listed companies from:
  - TWSE Open API (台股上市)
  - TPEX Open API (台股上櫃)
  - NASDAQ SymbolDirectory (美股 NASDAQ + NYSE/AMEX)

Results are bulk-upserted into the `stocks` table with track_price=False.
track_price is only set to True when a user adds a stock to their watchlist
or creates a transaction, so the scheduler only updates relevant tickers.
"""

import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock

logger = logging.getLogger(__name__)

_TW_LISTED_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
_TW_OTC_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
_NASDAQ_LISTED_URL = "https://ftp.nasdaqtrader.com/dynamic/SymbolDirectory/nasdaqlisted.txt"
_NASDAQ_OTHER_URL = "https://ftp.nasdaqtrader.com/dynamic/SymbolDirectory/otherlisted.txt"

_BATCH_SIZE = 500


async def _fetch_tw_listed(client: httpx.AsyncClient) -> list[dict]:
    """Fetch TWSE-listed stocks (上市)."""
    try:
        resp = await client.get(_TW_LISTED_URL, timeout=30)
        resp.raise_for_status()
        stocks = []
        for item in resp.json():
            code = item.get("公司代號", "").strip()
            name = item.get("公司簡稱", "").strip()
            if code and name:
                stocks.append({"ticker": f"{code}.TW", "name": name, "market": "TW", "currency": "TWD"})
        logger.info("Fetched %d TW listed stocks", len(stocks))
        return stocks
    except Exception as exc:
        logger.warning("Failed to fetch TW listed stocks: %s", exc)
        return []


async def _fetch_tw_otc(client: httpx.AsyncClient) -> list[dict]:
    """Fetch TPEX OTC stocks (上櫃)."""
    try:
        resp = await client.get(_TW_OTC_URL, timeout=30)
        resp.raise_for_status()
        stocks = []
        for item in resp.json():
            # TPEX API may use English or Chinese field names
            code = (item.get("SecuritiesCompanyCode") or item.get("公司代號") or "").strip()
            name = (item.get("CompanyAbbreviation") or item.get("公司簡稱") or "").strip()
            if code and name:
                stocks.append({"ticker": f"{code}.TW", "name": name, "market": "TW", "currency": "TWD"})
        logger.info("Fetched %d TW OTC stocks", len(stocks))
        return stocks
    except Exception as exc:
        logger.warning("Failed to fetch TW OTC stocks: %s", exc)
        return []


async def _fetch_nasdaq_listed(client: httpx.AsyncClient) -> list[dict]:
    """Fetch NASDAQ-listed stocks.

    File format (pipe-delimited):
      Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
    """
    try:
        resp = await client.get(_NASDAQ_LISTED_URL, timeout=30)
        resp.raise_for_status()
        stocks = []
        for line in resp.text.splitlines()[1:]:  # skip header
            if line.startswith("File Creation"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            symbol, name, _market_cat, test_issue = parts[0], parts[1], parts[2], parts[3]
            if test_issue.strip() == "Y" or not symbol.strip():
                continue
            stocks.append({"ticker": symbol.strip(), "name": name.strip(), "market": "US", "currency": "USD"})
        logger.info("Fetched %d NASDAQ listed stocks", len(stocks))
        return stocks
    except Exception as exc:
        logger.warning("Failed to fetch NASDAQ listed stocks: %s", exc)
        return []


async def _fetch_nasdaq_other(client: httpx.AsyncClient) -> list[dict]:
    """Fetch NYSE/AMEX stocks from NASDAQ 'other listed' file.

    File format (pipe-delimited):
      ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
    """
    try:
        resp = await client.get(_NASDAQ_OTHER_URL, timeout=30)
        resp.raise_for_status()
        stocks = []
        for line in resp.text.splitlines()[1:]:  # skip header
            if line.startswith("File Creation"):
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue
            symbol, name, test_issue = parts[0], parts[1], parts[6]
            if test_issue.strip() == "Y" or not symbol.strip():
                continue
            stocks.append({"ticker": symbol.strip(), "name": name.strip(), "market": "US", "currency": "USD"})
        logger.info("Fetched %d NYSE/AMEX stocks", len(stocks))
        return stocks
    except Exception as exc:
        logger.warning("Failed to fetch NYSE/AMEX stocks: %s", exc)
        return []


async def sync_catalog(db: AsyncSession) -> dict[str, int]:
    """Fetch full stock catalog from TWSE and NASDAQ, upsert into DB.

    - New tickers are inserted with track_price=False.
    - Existing tickers have their name updated from the authoritative catalog source.
      This corrects names that yfinance may have populated with wrong values
      (e.g. TW ETFs returning the fund manager name instead of the ETF name).
    - market, currency, track_price are never overwritten.
    - Returns {"added": N, "updated": N}.
    """
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _fetch_tw_listed(client),
            _fetch_tw_otc(client),
            _fetch_nasdaq_listed(client),
            _fetch_nasdaq_other(client),
        )

    all_stocks: list[dict] = []
    seen: set[str] = set()
    for group in results:
        for s in group:
            if s["ticker"] not in seen:
                seen.add(s["ticker"])
                all_stocks.append(s)

    if not all_stocks:
        logger.warning("Catalog sync: no stocks fetched from any source")
        return {"added": 0, "updated": 0}

    # Build lookup: ticker → catalog name
    catalog: dict[str, str] = {s["ticker"]: s["name"] for s in all_stocks}

    # Fetch existing stocks in one query
    existing_result = await db.execute(select(Stock))
    existing_stocks: dict[str, Stock] = {s.ticker: s for s in existing_result.scalars()}

    new_stocks: list[Stock] = []
    updated = 0

    for item in all_stocks:
        ticker = item["ticker"]
        if ticker in existing_stocks:
            stock = existing_stocks[ticker]
            if stock.name != item["name"]:
                stock.name = item["name"]
                updated += 1
        else:
            new_stocks.append(Stock(
                ticker=ticker,
                name=item["name"],
                market=item["market"],
                currency=item["currency"],
                track_price=False,
            ))

    for i in range(0, len(new_stocks), _BATCH_SIZE):
        db.add_all(new_stocks[i : i + _BATCH_SIZE])
        await db.flush()

    await db.commit()
    logger.info("Catalog sync complete: %d added, %d updated", len(new_stocks), updated)
    return {"added": len(new_stocks), "updated": updated}

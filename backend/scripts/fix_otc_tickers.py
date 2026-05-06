"""One-time migration script: rename OTC stock tickers from .TW to .TWO.

Usage:
    # In Docker
    docker compose exec backend python scripts/fix_otc_tickers.py

    # Local venv
    cd backend && python scripts/fix_otc_tickers.py
"""

import asyncio
import sys

import httpx
from sqlalchemy import update

sys.path.insert(0, ".")

from app.database import AsyncSessionLocal
from app.models.stock import Stock
from app.services.stock_catalog_service import _fetch_tw_otc


async def main() -> None:
    async with httpx.AsyncClient() as client:
        otc_stocks = await _fetch_tw_otc(client)

    if not otc_stocks:
        print("ERROR: Failed to fetch OTC stock list from TPEX API.")
        return

    # Extract codes from ticker "8069.TWO" → "8069"
    otc_codes = {item["ticker"].removesuffix(".TWO") for item in otc_stocks}
    print(f"Fetched {len(otc_codes)} OTC codes from TPEX API.")

    async with AsyncSessionLocal() as db:
        updated_total = 0
        for code in sorted(otc_codes):
            old_ticker = f"{code}.TW"
            new_ticker = f"{code}.TWO"
            result = await db.execute(
                update(Stock)
                .where(Stock.ticker == old_ticker)
                .values(ticker=new_ticker)
            )
            if result.rowcount:
                print(f"  {old_ticker} → {new_ticker}")
                updated_total += result.rowcount

        await db.commit()

    print(f"\nDone. Updated {updated_total} ticker(s).")


if __name__ == "__main__":
    asyncio.run(main())

"""APScheduler jobs for periodic stock price and exchange rate updates.

The scheduler is attached to the FastAPI lifespan in main.py and runs
inside the same asyncio event loop as the web server.
"""

import logging
from datetime import datetime
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.stock_service import batch_update_prices
from app.services.stock_service import update_exchange_rate

logger = logging.getLogger(__name__)


def _is_market_open() -> bool:
    """Return True if at least one market (TW or US) is currently open.

    Times are in UTC (weekdays only):
      - TWSE:  01:00–05:30 UTC  (09:00–13:30 UTC+8)
      - NYSE:  13:30–21:00 UTC  (09:30–16:00 ET, approximate; ignores DST)
    """
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    minutes = now.hour * 60 + now.minute
    tw_open = (1 * 60, 5 * 60 + 30)
    us_open = (13 * 60 + 30, 21 * 60)
    return (tw_open[0] <= minutes <= tw_open[1]) or (us_open[0] <= minutes <= us_open[1])


async def update_prices_job() -> None:
    if not _is_market_open():
        logger.debug("Markets closed, skipping price update")
        return

    logger.info("Running scheduled price update")
    async with AsyncSessionLocal() as db:
        updated = await batch_update_prices(db)
        await update_exchange_rate("USD", "TWD", db)
        logger.info("Scheduled update complete: %d stocks refreshed", updated)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_prices_job,
        trigger=IntervalTrigger(minutes=settings.PRICE_UPDATE_INTERVAL_MINUTES),
        id="price_update",
        replace_existing=True,
        max_instances=1,  # prevent overlap if a job run is slow
    )
    return scheduler

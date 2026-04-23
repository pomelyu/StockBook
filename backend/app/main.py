import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.database import engine
from app.models.stock import Stock
from app.models.user import User
from app.scheduler.price_updater import create_scheduler
from app.services.auth_service import hash_password
from app.services.stock_catalog_service import sync_catalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _background_catalog_sync() -> None:
    """Run catalog sync in background; errors are logged, not raised."""
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_catalog(db)
            logger.info("Background catalog sync complete: %s", result)
        except Exception as exc:
            logger.error("Background catalog sync failed: %s", exc)


async def _seed_admin_user() -> None:
    """Create the hardcoded admin user if it doesn't already exist."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.SEED_USERNAME))
        if result.scalar_one_or_none():
            return

        user = User(
            username=settings.SEED_USERNAME,
            email=settings.SEED_EMAIL,
            hashed_password=hash_password(settings.SEED_PASSWORD),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        await db.commit()
        logger.info("Seed user '%s' created", settings.SEED_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- startup ----------
    # Schema is managed by Alembic — run `alembic upgrade head` before starting.
    await _seed_admin_user()

    # Populate stock catalog on first run (non-blocking)
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(Stock))
    if count == 0:
        logger.info("Empty stock catalog — starting background sync")
        asyncio.create_task(_background_catalog_sync())

    scheduler = None
    if settings.ENABLE_SCHEDULER:
        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Price update scheduler started")

    yield

    # ---------- shutdown ----------
    if scheduler:
        scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(
    title="StockBook API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.admin import router as admin_router  # noqa: E402
# Register routers
from app.api.auth import router as auth_router  # noqa: E402
from app.api.stocks import router as stocks_router  # noqa: E402
from app.api.watchlist import router as watchlist_router  # noqa: E402

PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(stocks_router, prefix=PREFIX)
app.include_router(watchlist_router, prefix=PREFIX)
app.include_router(admin_router, prefix=PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}

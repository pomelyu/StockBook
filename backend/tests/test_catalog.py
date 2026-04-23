"""Tests for stock_catalog_service and POST /admin/catalog/sync."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.services.stock_catalog_service import sync_catalog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_fetchers(tw_listed=None, tw_otc=None, nasdaq=None, other=None):
    """Return monkeypatching helpers that replace all four fetch functions."""
    tw_listed = tw_listed or []
    tw_otc = tw_otc or []
    nasdaq = nasdaq or []
    other = other or []

    async def fake_tw_listed(client):
        return tw_listed

    async def fake_tw_otc(client):
        return tw_otc

    async def fake_nasdaq_listed(client):
        return nasdaq

    async def fake_nasdaq_other(client):
        return other

    return fake_tw_listed, fake_tw_otc, fake_nasdaq_listed, fake_nasdaq_other


def _patch_fetchers(monkeypatch, tw_listed=None, tw_otc=None, nasdaq=None, other=None):
    fl, fo, fn, fother = _make_fake_fetchers(tw_listed, tw_otc, nasdaq, other)
    monkeypatch.setattr("app.services.stock_catalog_service._fetch_tw_listed", fl)
    monkeypatch.setattr("app.services.stock_catalog_service._fetch_tw_otc", fo)
    monkeypatch.setattr("app.services.stock_catalog_service._fetch_nasdaq_listed", fn)
    monkeypatch.setattr("app.services.stock_catalog_service._fetch_nasdaq_other", fother)


# ---------------------------------------------------------------------------
# Unit tests — sync_catalog()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_catalog_inserts_new_stocks(db_session: AsyncSession, monkeypatch):
    _patch_fetchers(
        monkeypatch,
        tw_listed=[{"ticker": "2330.TW", "name": "台積電", "market": "TW", "currency": "TWD"}],
        nasdaq=[{"ticker": "AAPL", "name": "Apple Inc.", "market": "US", "currency": "USD"}],
    )

    result = await sync_catalog(db_session)

    assert result["added"] == 2
    assert result["updated"] == 0

    tickers_in_db = {row[0] for row in (await db_session.execute(select(Stock.ticker)))}
    assert "2330.TW" in tickers_in_db
    assert "AAPL" in tickers_in_db


@pytest.mark.asyncio
async def test_sync_catalog_new_stocks_have_track_price_false(db_session: AsyncSession, monkeypatch):
    _patch_fetchers(
        monkeypatch,
        nasdaq=[{"ticker": "MSFT", "name": "Microsoft", "market": "US", "currency": "USD"}],
    )

    await sync_catalog(db_session)

    result = await db_session.execute(select(Stock).where(Stock.ticker == "MSFT"))
    stock = result.scalar_one()
    assert stock.track_price is False


@pytest.mark.asyncio
async def test_sync_catalog_updates_existing_name(db_session: AsyncSession, monkeypatch):
    # Pre-insert a stock with a wrong name (e.g. from yfinance fallback)
    existing = Stock(ticker="GOOG", name="Wrong Name From yfinance", market="US", currency="USD", track_price=True)
    db_session.add(existing)
    await db_session.commit()

    _patch_fetchers(
        monkeypatch,
        nasdaq=[
            {"ticker": "GOOG", "name": "Alphabet Inc.", "market": "US", "currency": "USD"},
            {"ticker": "NVDA", "name": "NVIDIA", "market": "US", "currency": "USD"},
        ],
    )

    result = await sync_catalog(db_session)

    assert result["added"] == 1    # only NVDA
    assert result["updated"] == 1  # GOOG name corrected

    # Existing GOOG name should be updated from catalog
    goog = (await db_session.execute(select(Stock).where(Stock.ticker == "GOOG"))).scalar_one()
    assert goog.name == "Alphabet Inc."
    assert goog.track_price is True  # track_price unchanged


@pytest.mark.asyncio
async def test_sync_catalog_deduplicates_across_sources(db_session: AsyncSession, monkeypatch):
    # Same ticker from both nasdaq and other sources
    _patch_fetchers(
        monkeypatch,
        nasdaq=[{"ticker": "SPY", "name": "SPDR S&P 500 ETF", "market": "US", "currency": "USD"}],
        other=[{"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "market": "US", "currency": "USD"}],
    )

    result = await sync_catalog(db_session)

    assert result["added"] == 1  # deduplicated

    count_result = await db_session.execute(select(Stock).where(Stock.ticker == "SPY"))
    assert len(count_result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_sync_catalog_partial_failure_still_inserts(db_session: AsyncSession, monkeypatch):
    # tw_listed returns empty (simulating API failure), but nasdaq works
    _patch_fetchers(
        monkeypatch,
        tw_listed=[],
        nasdaq=[{"ticker": "TSLA", "name": "Tesla", "market": "US", "currency": "USD"}],
    )

    result = await sync_catalog(db_session)
    assert result["added"] == 1


# ---------------------------------------------------------------------------
# Integration tests — POST /admin/catalog/sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_catalog_sync_endpoint(
    client: AsyncClient, superuser_headers: dict, monkeypatch
):
    _patch_fetchers(
        monkeypatch,
        tw_listed=[{"ticker": "2454.TW", "name": "聯發科", "market": "TW", "currency": "TWD"}],
    )
    # Also patch sync_catalog called via the endpoint
    async def fake_sync(db):
        return {"added": 1, "skipped": 0}

    monkeypatch.setattr("app.api.admin.sync_catalog", fake_sync)

    resp = await client.post("/api/v1/admin/catalog/sync", headers=superuser_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "added" in data
    assert "updated" in data


@pytest.mark.asyncio
async def test_admin_catalog_sync_requires_superuser(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/admin/catalog/sync", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_catalog_sync_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/admin/catalog/sync")
    assert resp.status_code == 401

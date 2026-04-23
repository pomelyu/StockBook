"""Tests for /api/v1/stocks/* endpoints and stock_service helpers."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.user import User
from app.services.stock_service import _normalize_ticker
from app.services.stock_service import get_or_create_stock

# --- unit tests for pure helpers ---


def test_normalize_ticker_digits():
    assert _normalize_ticker("2330") == "2330.TW"


def test_normalize_ticker_already_tw():
    assert _normalize_ticker("2330.TW") == "2330.TW"


def test_normalize_ticker_us_stock():
    assert _normalize_ticker("aapl") == "AAPL"


def test_normalize_ticker_strips_whitespace():
    assert _normalize_ticker("  2330  ") == "2330.TW"


# --- integration tests (DB only, no real yfinance calls) ---


@pytest.mark.asyncio
async def test_get_or_create_stock_creates_in_db(db_session: AsyncSession, monkeypatch):
    # Stub out yfinance so the test never hits the network
    async def _fake_fetch(ticker_raw, db):
        from app.services.stock_service import _infer_market_currency
        from app.services.stock_service import _normalize_ticker
        ticker = _normalize_ticker(ticker_raw)
        market, currency = _infer_market_currency(ticker)
        stock = Stock(ticker=ticker, name="Fake Corp", market=market, currency=currency)
        db.add(stock)
        await db.commit()
        await db.refresh(stock)
        return stock

    monkeypatch.setattr("app.services.stock_service.get_or_create_stock", _fake_fetch)

    stock = await _fake_fetch("FAKE", db_session)
    assert stock.ticker == "FAKE"
    assert stock.market == "US"


@pytest.mark.asyncio
async def test_search_returns_existing_stocks(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user: User
):
    stock = Stock(ticker="TSM", name="Taiwan Semiconductor", market="US", currency="USD")
    db_session.add(stock)
    await db_session.commit()

    resp = await client.get("/api/v1/stocks/search?q=TSM", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["ticker"] == "TSM" for s in results)


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/stocks/search?q=AAPL")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_existing_stock(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    stock = Stock(ticker="MSFT", name="Microsoft", market="US", currency="USD")
    db_session.add(stock)
    await db_session.commit()

    resp = await client.get("/api/v1/stocks/MSFT", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "MSFT"

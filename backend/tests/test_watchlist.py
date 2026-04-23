"""Tests for /api/v1/watchlist/* endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import Watchlist


async def _seed_stock(db: AsyncSession, ticker: str = "AAPL") -> Stock:
    stock = Stock(ticker=ticker, name="Apple Inc.", market="US", currency="USD")
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


@pytest.mark.asyncio
async def test_list_watchlist_empty(client: AsyncClient, test_user: User, auth_headers: dict):
    resp = await client.get("/api/v1/watchlist/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_to_watchlist(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict, monkeypatch
):
    stock = await _seed_stock(db_session)

    # Stub get_or_create_stock so no yfinance call happens
    async def _fake_get_or_create(ticker_raw, db):
        return stock

    monkeypatch.setattr("app.api.watchlist.get_or_create_stock", _fake_get_or_create)

    resp = await client.post(
        "/api/v1/watchlist/",
        json={"ticker": "AAPL"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["note"] is None


@pytest.mark.asyncio
async def test_add_duplicate_watchlist_returns_409(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict, monkeypatch
):
    stock = await _seed_stock(db_session)

    async def _fake_get_or_create(ticker_raw, db):
        return stock

    monkeypatch.setattr("app.api.watchlist.get_or_create_stock", _fake_get_or_create)

    await client.post("/api/v1/watchlist/", json={"ticker": "AAPL"}, headers=auth_headers)
    resp = await client.post("/api/v1/watchlist/", json={"ticker": "AAPL"}, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_remove_from_watchlist(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, ticker="GOOG")
    entry = Watchlist(user_id=test_user.id, stock_id=stock.id)
    db_session.add(entry)
    await db_session.commit()

    resp = await client.delete("/api/v1/watchlist/GOOG", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_returns_404(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    resp = await client.delete("/api/v1/watchlist/NOPE", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/watchlist/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_watchlist_returns_added_stock(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, ticker="NVDA")
    entry = Watchlist(user_id=test_user.id, stock_id=stock.id)
    db_session.add(entry)
    await db_session.commit()

    resp = await client.get("/api/v1/watchlist/", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    tickers = [item["ticker"] for item in items]
    assert "NVDA" in tickers
    # Verify stock fields are fully populated (guards against lazy-load regression)
    item = next(i for i in items if i["ticker"] == "NVDA")
    assert item["name"] == "Apple Inc."
    assert item["market"] == "US"
    assert item["currency"] == "USD"

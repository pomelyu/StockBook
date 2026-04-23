"""Tests for Dividends CRUD API."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dividend import Dividend
from app.models.stock import Stock
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_stock(db: AsyncSession, ticker: str = "AAPL") -> Stock:
    stock = Stock(ticker=ticker, name=f"{ticker} Inc.", market="US", currency="USD")
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


async def _seed_dividend(
    db: AsyncSession,
    user: User,
    stock: Stock,
    dividend_type: str = "CASH",
    amount: str = "100",
    shares_received: str | None = None,
) -> Dividend:
    div = Dividend(
        user_id=user.id,
        stock_id=stock.id,
        dividend_type=dividend_type,
        amount=Decimal(amount),
        currency="USD",
        shares_received=Decimal(shares_received) if shares_received else None,
        ex_dividend_date=date(2025, 6, 1),
    )
    db.add(div)
    await db.commit()
    await db.refresh(div)
    return div


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_cash_dividend(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    await _seed_stock(db_session, "AAPL")

    resp = await client.post(
        "/api/v1/dividends/",
        json={
            "ticker": "AAPL",
            "dividend_type": "CASH",
            "amount": "50.00",
            "currency": "USD",
            "ex_dividend_date": "2025-06-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["dividend_type"] == "CASH"
    assert Decimal(data["amount"]) == Decimal("50.00")
    assert data["shares_received"] is None


@pytest.mark.asyncio
async def test_create_stock_dividend(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    await _seed_stock(db_session, "2330.TW")

    resp = await client.post(
        "/api/v1/dividends/",
        json={
            "ticker": "2330.TW",
            "dividend_type": "STOCK",
            "amount": "0",
            "currency": "TWD",
            "shares_received": "5",
            "ex_dividend_date": "2025-07-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["dividend_type"] == "STOCK"
    assert Decimal(data["shares_received"]) == Decimal("5")


@pytest.mark.asyncio
async def test_create_drip_dividend(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    await _seed_stock(db_session, "MSFT")

    resp = await client.post(
        "/api/v1/dividends/",
        json={
            "ticker": "MSFT",
            "dividend_type": "DRIP",
            "amount": "100.00",
            "currency": "USD",
            "shares_received": "0.3",
            "ex_dividend_date": "2025-06-15",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["dividend_type"] == "DRIP"
    assert Decimal(data["amount"]) == Decimal("100.00")
    assert Decimal(data["shares_received"]) == Decimal("0.3")


@pytest.mark.asyncio
async def test_stock_dividend_requires_shares_received(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    await _seed_stock(db_session, "AAPL")

    resp = await client.post(
        "/api/v1/dividends/",
        json={
            "ticker": "AAPL",
            "dividend_type": "STOCK",
            "amount": "0",
            "currency": "USD",
            "ex_dividend_date": "2025-06-01",
            # missing shares_received
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cash_dividend_rejects_shares_received(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    await _seed_stock(db_session, "AAPL")

    resp = await client.post(
        "/api/v1/dividends/",
        json={
            "ticker": "AAPL",
            "dividend_type": "CASH",
            "amount": "50",
            "currency": "USD",
            "shares_received": "2",   # should not be set for CASH
            "ex_dividend_date": "2025-06-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List / pagination / filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_dividends_pagination(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    for _ in range(5):
        await _seed_dividend(db_session, test_user, stock)

    resp = await client.get(
        "/api/v1/dividends/?page=1&page_size=3", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_dividends_filter_ticker(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    aapl = await _seed_stock(db_session, "AAPL")
    msft = await _seed_stock(db_session, "MSFT")
    await _seed_dividend(db_session, test_user, aapl)
    await _seed_dividend(db_session, test_user, msft)

    resp = await client.get("/api/v1/dividends/?ticker=AAPL", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_dividend_by_id(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    div = await _seed_dividend(db_session, test_user, stock)

    resp = await client.get(f"/api/v1/dividends/{div.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(div.id)


@pytest.mark.asyncio
async def test_get_dividend_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/dividends/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_other_users_dividend(
    client: AsyncClient, db_session: AsyncSession, superuser: User, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    div = await _seed_dividend(db_session, superuser, stock)

    resp = await client.get(f"/api/v1/dividends/{div.id}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_dividend(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    div = await _seed_dividend(db_session, test_user, stock, amount="100")

    resp = await client.put(
        f"/api/v1/dividends/{div.id}",
        json={"amount": "120.00", "note": "corrected"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["amount"]) == Decimal("120.00")
    assert data["note"] == "corrected"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_dividend(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    div = await _seed_dividend(db_session, test_user, stock)

    resp = await client.delete(f"/api/v1/dividends/{div.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/dividends/{div.id}", headers=auth_headers)
    assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dividends_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/dividends/")
    assert resp.status_code == 401

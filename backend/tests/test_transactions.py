"""Tests for Transactions CRUD API."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.transaction import Transaction
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


async def _seed_transaction(
    db: AsyncSession,
    user: User,
    stock: Stock,
    tx_type: str = "BUY",
    quantity: str = "10",
    price: str = "100",
) -> Transaction:
    tx = Transaction(
        user_id=user.id,
        stock_id=stock.id,
        transaction_type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal("0"),
        transaction_date=date(2025, 1, 1),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_buy_transaction(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    await _seed_stock(db_session, "AAPL")

    resp = await client.post(
        "/api/v1/transactions/",
        json={
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": "10",
            "price": "150.00",
            "fee": "1.50",
            "transaction_date": "2025-03-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["transaction_type"] == "BUY"
    assert Decimal(data["quantity"]) == Decimal("10")
    assert Decimal(data["fee"]) == Decimal("1.50")


@pytest.mark.asyncio
async def test_create_sell_after_buy(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, "MSFT")
    await _seed_transaction(db_session, test_user, stock, "BUY", "20", "200")

    resp = await client.post(
        "/api/v1/transactions/",
        json={
            "ticker": "MSFT",
            "transaction_type": "SELL",
            "quantity": "10",
            "price": "250.00",
            "transaction_date": "2025-04-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["transaction_type"] == "SELL"


@pytest.mark.asyncio
async def test_sell_exceeds_position_rejected(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, "TSLA")
    await _seed_transaction(db_session, test_user, stock, "BUY", "5", "300")

    resp = await client.post(
        "/api/v1/transactions/",
        json={
            "ticker": "TSLA",
            "transaction_type": "SELL",
            "quantity": "10",   # more than the 5 we own
            "price": "350.00",
            "transaction_date": "2025-05-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sell_with_no_position_rejected(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    await _seed_stock(db_session, "NVDA")

    resp = await client.post(
        "/api/v1/transactions/",
        json={
            "ticker": "NVDA",
            "transaction_type": "SELL",
            "quantity": "1",
            "price": "400.00",
            "transaction_date": "2025-05-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List / pagination / filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_transactions_pagination(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, "AAPL")
    for _ in range(5):
        await _seed_transaction(db_session, test_user, stock)

    resp = await client.get(
        "/api/v1/transactions/?page=1&page_size=3", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 3


@pytest.mark.asyncio
async def test_list_transactions_filter_ticker(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    aapl = await _seed_stock(db_session, "AAPL")
    msft = await _seed_stock(db_session, "MSFT")
    await _seed_transaction(db_session, test_user, aapl)
    await _seed_transaction(db_session, test_user, msft)

    resp = await client.get("/api/v1/transactions/?ticker=AAPL", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_list_transactions_filter_type(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session, "AAPL")
    await _seed_transaction(db_session, test_user, stock, "BUY", "20")
    await _seed_transaction(db_session, test_user, stock, "SELL", "5")

    resp = await client.get(
        "/api/v1/transactions/?transaction_type=BUY", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["transaction_type"] == "BUY"


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_transaction_by_id(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    tx = await _seed_transaction(db_session, test_user, stock)

    resp = await client.get(f"/api/v1/transactions/{tx.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(tx.id)


@pytest.mark.asyncio
async def test_get_transaction_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/transactions/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_other_users_transaction(
    client: AsyncClient, db_session: AsyncSession, superuser: User, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    # Transaction belongs to superuser, not test_user
    tx = await _seed_transaction(db_session, superuser, stock)

    resp = await client.get(f"/api/v1/transactions/{tx.id}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_transaction(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    tx = await _seed_transaction(db_session, test_user, stock, price="100")

    resp = await client.put(
        f"/api/v1/transactions/{tx.id}",
        json={"price": "120.50", "note": "updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["price"]) == Decimal("120.50")
    assert data["note"] == "updated"


@pytest.mark.asyncio
async def test_update_sell_quantity_exceeding_position_rejected(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    await _seed_transaction(db_session, test_user, stock, "BUY", "10")
    sell_tx = await _seed_transaction(db_session, test_user, stock, "SELL", "5")

    resp = await client.put(
        f"/api/v1/transactions/{sell_tx.id}",
        json={"quantity": "15"},   # exceeds position of 10
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_transaction(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    tx = await _seed_transaction(db_session, test_user, stock)

    resp = await client.delete(f"/api/v1/transactions/{tx.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/transactions/{tx.id}", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_buy_that_covers_sell_rejected(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    stock = await _seed_stock(db_session)
    buy_tx = await _seed_transaction(db_session, test_user, stock, "BUY", "10")
    await _seed_transaction(db_session, test_user, stock, "SELL", "10")

    # Deleting the BUY would leave position = -10
    resp = await client.delete(f"/api/v1/transactions/{buy_tx.id}", headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transactions_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/transactions/")
    assert resp.status_code == 401

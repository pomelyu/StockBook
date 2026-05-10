"""Accounts CRUD endpoints."""

import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.account import Account
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.account import AccountResponse
from app.schemas.account import AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get(
    "/",
    response_model=list[AccountResponse],
    summary="List accounts",
    response_description="使用者的所有帳戶清單",
)
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取得目前登入使用者的所有帳戶，依建立時間升序排列。
    """
    result = await db.execute(
        select(Account)
        .where(Account.user_id == current_user.id)
        .order_by(Account.created_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
    response_description="新建立的帳戶",
)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    新增一個帳戶。

    - `market` 固定為 TW（台股）或 US（美股），建立後不可更改
    - 同一使用者可建立多個相同 market 的帳戶
    """
    account = Account(
        user_id=current_user.id,
        name=body.name,
        market=body.market,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    response_description="更新後的帳戶",
)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    修改帳戶名稱。

    - 只能修改自己的帳戶
    - `market` 欄位不可更改
    """
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    account.name = body.name
    await db.commit()
    await db.refresh(account)
    return account


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
)
async def delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刪除帳戶。

    - 帳戶底下有交易紀錄或股息紀錄時，回傳 **400**（請先移除紀錄）
    - 只能刪除自己的帳戶
    """
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    tx_count = await db.scalar(
        select(func.count()).where(Transaction.account_id == account_id)
    )
    if tx_count and tx_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with existing transactions",
        )

    div_count = await db.scalar(
        select(func.count()).where(Dividend.account_id == account_id)
    )
    if div_count and div_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with existing dividends",
        )

    await db.delete(account)
    await db.commit()

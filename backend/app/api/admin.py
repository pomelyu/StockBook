from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser
from app.database import get_db
from app.models.user import User
from app.services.stock_catalog_service import sync_catalog
from app.services.stock_service import batch_update_prices
from app.services.stock_service import update_exchange_rate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/prices/refresh",
    summary="Refresh tracked stock prices",
    response_description="更新的股票數量",
)
async def refresh_prices(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    手動觸發股價更新（等同 scheduler 的單次執行）。

    - 只更新 `track_price=True` 的股票（有人加入 watchlist 或持有的）
    - 同時更新 USD/TWD 匯率
    - 需要 superuser 權限
    """
    updated = await batch_update_prices(db)
    await update_exchange_rate("USD", "TWD", db)
    return {"updated_stocks": updated}


@router.post(
    "/catalog/sync",
    summary="Sync stock catalog",
    response_description="新增與略過的股票數量",
)
async def catalog_sync(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    從 TWSE、TPEX、NASDAQ 重新同步完整股票清單。

    - 新股票以 `track_price=False` 寫入，不影響現有追蹤設定
    - 已存在的 ticker 略過（不覆寫名稱）
    - 適合在有新 IPO 或需要刷新清單時手動觸發
    - 需要 superuser 權限
    """
    result = await sync_catalog(db)
    return result

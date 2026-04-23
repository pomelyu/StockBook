import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import Field


class WatchlistItemResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Watchlist 項目唯一識別碼")
    ticker: str = Field(..., description="yfinance 標準化 ticker（如 2330.TW、AAPL）")
    name: str | None = Field(None, description="股票名稱")
    market: str = Field(..., description="市場代碼：TW 或 US")
    currency: str = Field(..., description="交易貨幣：TWD 或 USD")
    last_price: Decimal | None = Field(None, description="最新快取股價；由 scheduler 定期更新，非即時")
    price_updated_at: datetime | None = Field(None, description="last_price 最後更新時間（UTC）")
    note: str | None = Field(None, description="使用者備註")
    added_at: datetime = Field(..., description="加入 watchlist 的時間（UTC）")

    model_config = {"from_attributes": True}


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., description="股票 ticker，台股輸入純數字即可（如 2330），系統自動加上 .TW 後綴")
    note: str | None = Field(None, description="備註（選填）")

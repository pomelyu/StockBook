import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StockResponse(BaseModel):
    id: uuid.UUID = Field(..., description="股票唯一識別碼")
    ticker: str = Field(..., description="yfinance 標準化 ticker（台股加 .TW 後綴，如 2330.TW；美股大寫，如 AAPL）")
    name: str | None = Field(None, description="股票名稱，初次建立時從 yfinance 取得，可能為 null")
    market: str = Field(..., description="市場代碼：TW（台股）或 US（美股）")
    currency: str = Field(..., description="交易貨幣：TWD 或 USD")
    last_price: Decimal | None = Field(None, description="最新快取股價；APScheduler 定期更新，非即時")
    price_updated_at: datetime | None = Field(None, description="last_price 最後更新時間（UTC）")

    model_config = {"from_attributes": True}

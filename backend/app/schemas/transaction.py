import uuid
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class TransactionCreate(BaseModel):
    ticker: str = Field(..., description="股票代號，台股純數字會自動轉為 .TW 格式（例：2330 → 2330.TW）")
    transaction_type: Literal["BUY", "SELL"] = Field(..., description="交易類型：BUY（買入）或 SELL（賣出）")
    quantity: Decimal = Field(..., gt=0, description="交易股數（支援零股，需大於 0）")
    price: Decimal = Field(..., ge=0, description="每股價格（原始貨幣，需大於等於 0）")
    fee: Decimal = Field(Decimal("0"), ge=0, description="手續費總額（影響 FIFO 成本計算，預設為 0）")
    transaction_date: date = Field(..., description="交割日（格式：YYYY-MM-DD）")
    note: str | None = Field(None, description="備註（可選）")


class TransactionUpdate(BaseModel):
    transaction_type: Literal["BUY", "SELL"] | None = Field(None, description="交易類型")
    quantity: Decimal | None = Field(None, gt=0, description="交易股數")
    price: Decimal | None = Field(None, ge=0, description="每股價格")
    fee: Decimal | None = Field(None, ge=0, description="手續費")
    transaction_date: date | None = Field(None, description="交割日")
    note: str | None = Field(None, description="備註")


class TransactionResponse(BaseModel):
    id: uuid.UUID = Field(..., description="交易紀錄 ID")
    ticker: str = Field(..., description="股票代號")
    stock_name: str | None = Field(None, description="股票名稱")
    transaction_type: str = Field(..., description="BUY 或 SELL")
    quantity: Decimal = Field(..., description="交易股數")
    price: Decimal = Field(..., description="每股價格（原始貨幣）")
    fee: Decimal = Field(..., description="手續費")
    transaction_date: date = Field(..., description="交割日")
    note: str | None = Field(None, description="備註")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="最後更新時間")

    model_config = {"from_attributes": True}

import uuid
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class DividendCreate(BaseModel):
    ticker: str = Field(..., description="股票代號，台股純數字會自動轉為 .TW 格式")
    dividend_type: Literal["CASH", "STOCK", "DRIP"] = Field(
        "CASH",
        description=(
            "股息類型：CASH（現金股息）、STOCK（配股，股票股息）、DRIP（股息再投入購股）。"
            "STOCK 和 DRIP 類型須填入 shares_received。"
        ),
    )
    amount: Decimal = Field(..., ge=0, description="實際收到的現金金額（STOCK 配股填 0）")
    currency: str = Field(..., description="幣別（例：TWD、USD）")
    shares_received: Decimal | None = Field(
        None, gt=0, description="取得股數（STOCK / DRIP 類型必填，CASH 留空）"
    )
    ex_dividend_date: date = Field(..., description="除息日（格式：YYYY-MM-DD）")
    payment_date: date | None = Field(None, description="配息日（可選）")
    note: str | None = Field(None, description="備註（可選）")

    @model_validator(mode="after")
    def validate_shares_received(self) -> "DividendCreate":
        if self.dividend_type in ("STOCK", "DRIP") and self.shares_received is None:
            raise ValueError(f"shares_received is required for dividend_type={self.dividend_type}")
        if self.dividend_type == "CASH" and self.shares_received is not None:
            raise ValueError("shares_received should not be set for CASH dividends")
        return self


class DividendUpdate(BaseModel):
    dividend_type: Literal["CASH", "STOCK", "DRIP"] | None = Field(None, description="股息類型")
    amount: Decimal | None = Field(None, ge=0, description="現金金額")
    currency: str | None = Field(None, description="幣別")
    shares_received: Decimal | None = Field(None, gt=0, description="取得股數")
    ex_dividend_date: date | None = Field(None, description="除息日")
    payment_date: date | None = Field(None, description="配息日")
    note: str | None = Field(None, description="備註")


class DividendResponse(BaseModel):
    id: uuid.UUID = Field(..., description="股息紀錄 ID")
    ticker: str = Field(..., description="股票代號")
    stock_name: str | None = Field(None, description="股票名稱")
    dividend_type: str = Field(..., description="CASH、STOCK 或 DRIP")
    amount: Decimal = Field(..., description="現金金額")
    currency: str = Field(..., description="幣別")
    shares_received: Decimal | None = Field(None, description="取得股數（STOCK / DRIP 才有值）")
    ex_dividend_date: date = Field(..., description="除息日")
    payment_date: date | None = Field(None, description="配息日")
    note: str | None = Field(None, description="備註")
    created_at: datetime = Field(..., description="建立時間")

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="帳戶名稱（例：富邦、TW-預設）")
    market: Literal["TW", "US"] = Field(..., description="市場別：TW（台股）或 US（美股）")


class AccountUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="帳戶名稱")


class AccountResponse(BaseModel):
    id: uuid.UUID = Field(..., description="帳戶 ID")
    name: str = Field(..., description="帳戶名稱")
    market: str = Field(..., description="市場別：TW 或 US")
    created_at: datetime = Field(..., description="建立時間")

    model_config = {"from_attributes": True}

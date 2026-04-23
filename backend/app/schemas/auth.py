import uuid

from pydantic import BaseModel
from pydantic import Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="帳號名稱")
    password: str = Field(..., description="明文密碼（傳輸請使用 HTTPS）")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="短效 JWT，用於 API 請求的 Authorization header（預設 60 分鐘）")
    refresh_token: str = Field(..., description="長效 JWT，用於換發新 access token（預設 30 天）")
    token_type: str = Field("bearer", description="Token 類型，固定為 bearer")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="先前取得的 refresh token")


class UserResponse(BaseModel):
    id: uuid.UUID = Field(..., description="使用者唯一識別碼")
    username: str = Field(..., description="帳號名稱")
    email: str = Field(..., description="電子郵件")
    is_active: bool = Field(..., description="帳號是否啟用；停用的帳號無法登入")
    is_superuser: bool = Field(..., description="是否為超級管理員，可存取 /admin 端點")

    model_config = {"from_attributes": True}
